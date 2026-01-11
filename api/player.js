// Vercel Serverless Function - Riot API 호출
// 사용법: /api/player?name=단바오&tag=owo

module.exports = async function handler(req, res) {
    // CORS 설정
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    
    const { name, tag } = req.query;
    
    if (!name || !tag) {
        return res.status(400).json({ 
            error: 'name과 tag 파라미터가 필요합니다',
            example: '/api/player?name=단바오&tag=owo'
        });
    }
    
    // Vercel 환경변수에서 API 키 가져오기
    const API_KEY = process.env.RIOT_API_KEY;
    
    if (!API_KEY) {
        return res.status(500).json({ 
            error: 'RIOT_API_KEY 환경변수가 설정되지 않았습니다' 
        });
    }
    
    try {
        const result = await getPlayerData(name, tag, API_KEY);
        return res.status(200).json(result);
    } catch (error) {
        return res.status(500).json({ 
            error: error.message,
            name: name,
            tag: tag
        });
    }
};

async function getPlayerData(gameName, tagLine, apiKey) {
    const data = {
        riotId: `${gameName}#${tagLine}`,
        puuid: null,
        summoner: null,
        rank: null,
        topChampions: [],
        error: null
    };
    
    // 1. Riot ID로 PUUID 조회 (ACCOUNT-V1)
    const accountUrl = `https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?api_key=${apiKey}`;
    
    const accountRes = await fetch(accountUrl);
    if (!accountRes.ok) {
        throw new Error(`계정 조회 실패: ${accountRes.status}`);
    }
    const accountData = await accountRes.json();
    data.puuid = accountData.puuid;
    
    // 2. PUUID로 소환사 정보 조회 (SUMMONER-V4)
    const summonerUrl = `https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/${data.puuid}?api_key=${apiKey}`;
    
    const summonerRes = await fetch(summonerUrl);
    if (!summonerRes.ok) {
        throw new Error(`소환사 조회 실패: ${summonerRes.status}`);
    }
    const summonerData = await summonerRes.json();
    data.summoner = {
        id: summonerData.id,
        name: summonerData.name,
        level: summonerData.summonerLevel,
        profileIconId: summonerData.profileIconId
    };
    
    // 3. 소환사 ID로 랭크 정보 조회 (LEAGUE-V4)
    const leagueUrl = `https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/${summonerData.id}?api_key=${apiKey}`;
    
    const leagueRes = await fetch(leagueUrl);
    if (leagueRes.ok) {
        const leagueData = await leagueRes.json();
        // 솔로랭크 찾기
        const soloRank = leagueData.find(q => q.queueType === 'RANKED_SOLO_5x5');
        if (soloRank) {
            data.rank = {
                tier: soloRank.tier,
                rank: soloRank.rank,
                lp: soloRank.leaguePoints,
                wins: soloRank.wins,
                losses: soloRank.losses,
                winRate: Math.round((soloRank.wins / (soloRank.wins + soloRank.losses)) * 100)
            };
        } else {
            data.rank = { tier: 'UNRANKED', rank: '', lp: 0, wins: 0, losses: 0, winRate: 0 };
        }
    }
    
    // 4. 챔피언 숙련도 조회 (CHAMPION-MASTERY-V4) - 상위 3개
    const masteryUrl = `https://kr.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/${data.puuid}/top?count=3&api_key=${apiKey}`;
    
    const masteryRes = await fetch(masteryUrl);
    if (masteryRes.ok) {
        const masteryData = await masteryRes.json();
        data.topChampions = masteryData.map(m => ({
            championId: m.championId,
            level: m.championLevel,
            points: m.championPoints
        }));
    }
    
    return data;
}
