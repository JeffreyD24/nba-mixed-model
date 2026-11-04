"""Out-of-sample checks of trends flagged in run_all.py, on 2011-12..2018-19 SBR openers (regular season only, pre-COVID, before any v4 training data)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE)); os.chdir(HERE)

import pandas as pd, numpy as np, json
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
S=pd.read_csv(REPO + '/data/external/sbr/sbr_nba_2011_2021_clean.csv.gz')
S=S[(S.total_trusted==1)&(S.open_ok==1)].copy(); S['date']=pd.to_datetime(S.date)
END={2011:'2012-04-26',2012:'2013-04-17',2013:'2014-04-16',2014:'2015-04-15',2015:'2016-04-13',2016:'2017-04-12',2017:'2018-04-11',2018:'2019-04-10'}
S=S[S.season.isin(END)]; S=S[S.date<=S.season.map(END).pipe(pd.to_datetime)]
S['act']=S.home_final+S.away_final; S['yo']=S.act-S.open_over_under
S=S[(S.open_over_under>150)&(S.act>120)].sort_values('date')
S['m']=S.date.dt.month
out={}
def ln(k,t): out[k]=t; print(k,t)
ln('n',f"{len(S)} regular-season games with trusted openers, 2011-12 to 2018-19 ({S.season.nunique()} seasons)")
# 1 month effect
mm=S.groupby('m').yo.agg(['mean','count']); a=smf.ols('yo ~ C(m)',S).fit()
from statsmodels.stats.anova import anova_lm
F=anova_lm(a)
apr=S[S.m==4].yo; rest=S[S.m!=4].yo; jan=S[S.m==1].yo
ta=stats.ttest_ind(apr,rest,equal_var=False); tj=stats.ttest_ind(jan,S[S.m!=1].yo,equal_var=False)
ln('month',f"(final - opener) by month: "+", ".join(f"{pd.Timestamp(2000,int(m),1).strftime('%b')} {r['mean']:+.2f} (n={int(r['count'])})" for m,r in mm.reindex([10,11,12,1,2,3,4]).iterrows())+
   f". Month ANOVA p={F['PR(>F)'].iloc[0]:.3f}. April vs rest {apr.mean()-rest.mean():+.2f}, Welch p={ta.pvalue:.3f}; April over the opener {np.mean(apr>0):.1%} (n={len(apr)}). January vs rest {jan.mean()-S[S.m!=1].yo.mean():+.2f}, p={tj.pvalue:.3f}.")
by=S[S.m==4].groupby('season').yo.mean()
ln('april_by_season',"April by season: "+", ".join(f"{s}-{str(s+1)[2:]} {v:+.1f}" for s,v in by.items()))
# 2 altitude
S['alt']=S.home_team.isin(['Nuggets','Jazz']).astype(int)
fa=smf.ols('yo ~ alt',S).fit()
ln('altitude',f"Denver/Utah home games vs opener: {fa.params.alt:+.2f} pts (SE {fa.bse.alt:.2f}, p={fa.pvalues.alt:.3f}); over rate {S[S.alt==1].yo.gt(0).mean():.1%} (n={S.alt.sum()}). "
   +"By season: "+", ".join(f"{s}-{str(s+1)[2:]} {v:+.1f}" for s,v in S[S.alt==1].groupby('season').yo.mean().items()))
# 3 early season games (either team in its first 10)
tl=pd.concat([S[['date','home_team']].rename(columns={'home_team':'t'}).assign(i=S.index),S[['date','away_team']].rename(columns={'away_team':'t'}).assign(i=S.index)])
tl=tl.merge(S[['season']],left_on='i',right_index=True).sort_values('date'); tl['k']=tl.groupby(['season','t']).cumcount()
kmin=tl.groupby('i').k.min(); S['early']=(kmin.reindex(S.index)<10).astype(int)
fe=smf.ols('yo ~ early',S).fit()
ln('early',f"Games where a team is in its first 10: {fe.params.early:+.2f} pts vs opener relative to later games (p={fe.pvalues.early:.3f}); mean {S[S.early==1].yo.mean():+.2f} (n={S.early.sum()}) vs {S[S.early==0].yo.mean():+.2f}. Opener MAE early {S[S.early==1].yo.abs().mean():.2f} vs later {S[S.early==0].yo.abs().mean():.2f}.")
# 4 heteroscedasticity
import statsmodels.api as sm
r=S.yo-S.yo.mean(); bp=het_breuschpagan(r,sm.add_constant(S[['open_over_under']]))
q=S.groupby(pd.qcut(S.open_over_under,5)).yo.std()
ln('spread',f"Error spread grows with the opener: Breusch-Pagan p={bp[1]:.2g}; SD by opener quintile "+", ".join(f"{iv.mid:.0f}:{v:.1f}" for iv,v in q.items())+".")
# 5 skew / right tail
ln('skew',f"(final - opener) skewness {stats.skew(S.yo):+.3f}, mean {S.yo.mean():+.2f}, median {S.yo.median():+.2f}; share beyond +30 {np.mean(S.yo>30):.2%} vs below -30 {np.mean(S.yo<-30):.2%}.")
# 6 over-team persistence (selection)
tl2=pd.concat([S[['season','date','home_team','yo']].rename(columns={'home_team':'t'}),S[['season','date','away_team','yo']].rename(columns={'away_team':'t'})]).sort_values('date')
tl2=tl2[tl2.yo!=0]; tl2['ov']=(tl2.yo>0).astype(float); tl2['k']=tl2.groupby(['season','t']).cumcount()
D=pd.concat([tl2[tl2.k<41].groupby(['season','t']).ov.mean(),tl2[tl2.k>=41].groupby(['season','t']).ov.mean()],axis=1,keys=['h1','h2']).dropna()
rr=stats.pearsonr(D.h1,D.h2); top=D[D.h1>=D.h1.quantile(.8)]
ln('over_teams',f"Team over% first 41 vs rest (vs opener): r={rr[0]:+.2f} (p={rr[1]:.2f}, {len(D)} team-seasons); top-20% teams {top.h1.mean():.1%} -> {top.h2.mean():.1%}.")
json.dump(out,open('oos.json','w'),indent=1)
