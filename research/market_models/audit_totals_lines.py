import pandas as pd, glob, sys
fs=sorted(glob.glob('data/odds_history/nba/*.csv.gz'))
d=pd.concat([pd.read_csv(f) for f in fs])
d=d[d.market=='totals']
d['snap']=pd.to_datetime(d.snapshot_utc).dt.tz_convert('America/New_York').dt.tz_localize(None)
d['tip']=pd.to_datetime(d.commence_et)
d['lead_h']=(d.tip-d.snap).dt.total_seconds()/3600
d=d[d.lead_h>0]
d['season']=d.tip.apply(lambda t:t.year+1 if t.month>=8 else t.year)
print('books:',d.book.value_counts().to_dict())
g=d.groupby(['season','book']).agg(games=('event_id','nunique'),snaps=('snapshot_utc','nunique'))
fl=d.groupby(['season','book','event_id']).lead_h.agg(['max','min']).reset_index()
fl2=fl.groupby(['season','book']).agg(first_lead_med=('max','median'),last_lead_med=('min','median'),pct_last_under1h=('min',lambda s:(s<=1).mean()))
print(g.join(fl2).round(2).to_string())
# snapshots per game
sp=d.groupby(['season','event_id']).snapshot_utc.nunique().groupby('season').median()
print('median snapshots per game by season\n',sp)
# snapshot cadence
s=d.drop_duplicates(['season','snapshot_utc']).sort_values('snap')
print('median gap between snapshots (h) by season:', s.groupby('season').snap.apply(lambda x:x.diff().dt.total_seconds().median()/3600).round(2).to_dict())
# first line vs close per book: open->close move
f=d[d.outcome=='Over'].sort_values('snap')
oc=f.groupby(['season','book','event_id']).point.agg(['first','last']).reset_index()
oc['absmove']=(oc['last']-oc['first']).abs()
print(oc.groupby('book').absmove.mean().round(2).to_dict())
# Pinnacle vs DK at first common & close
p=oc.pivot_table(index=['season','event_id'],columns='book',values=['first','last'])
for k in ['first','last']:
    x=(p[k]['pinnacle']-p[k]['draftkings']).dropna()
    print(k,'pin-dk diff: mean',round(x.mean(),2),'mean abs',round(x.abs().mean(),2),'% equal',round((x==0).mean(),2),'n',len(x))
oc.to_csv('/tmp/claude-0/-home-claude/c60f57b9-05a2-5b9e-abc9-71598bf31af1/scratchpad/open_close_by_book.csv',index=False)
