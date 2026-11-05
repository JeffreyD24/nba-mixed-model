# DraftKings via curl_cffi probe, 2026-11-05 22:46 UTC (GitHub runner)

| target | impersonate | HTTP | bytes | note |
|---|---|---|---|---|
| NBA dkusct | chrome124 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NBA dkusct | chrome131 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NBA dkusct | safari17_0 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NHL dkusct | chrome124 | 200 | 82218 | events 14: VGK Golden Knights @ DET Red Wings; UTA Mammoth @ MTL Canadiens; STL Blues @ NJ Devils; CAR Hurricanes @ NY Islanders; PHI Flyers @ NY Rangers; CHI Blackhawks @ TB Lightning |
| NHL dkusct | chrome131 | 200 | 82218 | events 14: VGK Golden Knights @ DET Red Wings; UTA Mammoth @ MTL Canadiens; STL Blues @ NJ Devils; CAR Hurricanes @ NY Islanders; PHI Flyers @ NY Rangers; CHI Blackhawks @ TB Lightning |
| NHL dkusct | safari17_0 | 200 | 82218 | events 14: VGK Golden Knights @ DET Red Wings; UTA Mammoth @ MTL Canadiens; STL Blues @ NJ Devils; CAR Hurricanes @ NY Islanders; PHI Flyers @ NY Rangers; CHI Blackhawks @ TB Lightning |
| NBA dkusnj | chrome124 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NBA dkusnj | chrome131 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NBA dkusnj | safari17_0 | 200 | 56518 | events 6: ORL Magic @ PHO Suns; MIA Heat @ GS Warriors; PHI 76ers @ CLE Cavaliers; MIN Timberwolves @ NO Pelicans; TOR Raptors @ MIL Bucks; SA Spurs @ SAC Kings |
| NBA page | chrome124 | 200 | 1910508 | <!doctype html> <html lang="en">   <head>     <meta charset="utf-8">     <meta http-equiv= |
| NBA page | chrome131 | 200 | 1910508 | <!doctype html> <html lang="en">   <head>     <meta charset="utf-8">     <meta http-equiv= |
| NBA page | safari17_0 | 200 | 1910582 | <!doctype html> <html lang="en">   <head>     <meta charset="utf-8">     <meta http-equiv= |

## NBA dkusct layout
top-level keys: ['sports', 'leagues', 'events', 'markets', 'selections', 'categories', 'subcategories', 'subscriptionPartials']
counts: sports=1, leagues=1, events=6, markets=18, selections=36, categories=28, subcategories=224
first sports: {"id": "2", "seoIdentifier": "Basketball", "name": "Basketball", "sortOrder": 59}
first leagues: {"id": "42648", "name": "NBA", "sportId": "2", "sortOrder": 4858, "tags": ["OSB", "FeaturedSubcategory", "SGP", "SgpDynamicOdds", "YourBetEligible", "EarlyExit", "EarlyExitPlus", "PlayerStack", "PrePack", "Featured", "FavoriteableFromPage"], "regions": [{"id": "227", "name": "United States"}], "isTeamSwap": true, "featured": true}
first events: {"id": "34937358", "seoIdentifier": "ORL Magic @ PHO Suns", "sportId": "2", "leagueId": "42648", "name": "ORL Magic @ PHO Suns", "startEventDate": "2026-11-06T02:10:00.0000000Z", "participants": [{"id": "32949", "name": "PHO Suns", "venueRole": "Home", "type": "Team", "metadata": {"retailRotNumber": "301", "rosettaTeamId": "32949", "rosettaTeamName": "Suns", "shortName": "PHO", "teamColor": "#1D1160", "teamColorSecondary": "#E56020", "teamColorTertiary": "#000000"}, "sortOrder": 2, "seoIdentifier": "Suns", "isNationalTeam": false, "countryCode": "US"}, {"id": "32945", "name": "ORL Magic", "venueRole": "Away", "type": "Team", "metadata": {"retailRotNumber": "300", "rosettaTeamId": "32945", "r
first markets: {"id": "1_87028693", "eventId": "34937358", "sportId": "2", "leagueId": "42648", "name": "Moneyline", "subcategoryId": 4511, "marketType": {"id": "1_0", "betOfferTypeId": 2, "name": "Moneyline"}, "subscriptionKey": "league-events-42648", "sortOrder": 187028693, "tags": ["SGP", "YourBetEligible", "Cashout", "FeaturedSubcategory", "OSB", "Default", "PrimaryMarket"], "main": true, "dynamicMetadata": {}}
first selections: {"id": "0HC87089595N1550_3", "marketId": "2_87089595", "label": "SA Spurs", "displayOdds": {"american": "\u2212110", "decimal": "1.90", "fractional": "10/11", "percentage": "52%", "multiplier": "1.90x"}, "trueOdds": 1.90909091, "points": -15.5, "outcomeType": "Away", "participants": [{"id": "32955", "name": "SA Spurs", "type": "Team", "seoIdentifier": "Spurs", "venueRole": "Away", "isNationalTeam": false, "countryCode": "US", "metadata": {"sdid": "19948"}}], "sortOrder": -15501, "tags": ["MainPointLine", "SGP", "OSB"], "main": true, "metadata": {}}
first categories: {"id": 487, "name": "Game Lines", "sortOrder": 487, "tags": ["SGP"]}
first subcategories: {"id": 15644, "categoryId": 519, "name": "Division Winner", "componentId": 29, "sortOrder": 8627, "tags": []}
