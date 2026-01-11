// Vercel Serverless Function - Riot API 호출 (풀버전)
// 사용법: /api/player?name=단바오&tag=owo

// 챔피언 ID → 이름 매핑
let championData = null;

async function getChampionData() {
    if (championData) return championData;
    
    try {
        const versionRes = await fetch('https://ddragon.leagueoflegends.com/api/versions.json');
        const versions = await versionRes.json();
        const latestVersion = versions[0];
        
        const champRes = await fetch(`https://ddragon.leagueoflegends.com/cdn/${latestVersion}/data/ko_KR/champion.json`);
        const champJson = await champRes.json();
        
        championData = { version: latestVersion };
        for (const [key, value] of Object.entries(champJson.data)) {
            championData[value.key] = {
                id: key,
                name: value.name,
                image: `https://ddragon.leagueoflegends.com/cdn/${latestVersion}/img/champion/${value.image.full}`
            };
        }
        return championData;
    } catch (e) {
        return { version: '14.24.1' };
    }
}

module.exports = async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    
    const { name, tag } = req.query;
    
    if (!name || !tag) {
        return res.status(400).json({ 
            error: 'name과 tag 파라미터가 필요합니다',
            example: '/api/player?name=단바오&tag=owo'
        });
    }
    
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
    const champions = await getChampionData();
    
    const data = {
        riotId: `${gameName}#${tagLine}`,
        puuid: null,
        summoner: null,
        soloRank: null,
        flexRank: null,
        topChampions: [],
        recentMatches: [],
        recentStats: null,  // 최근 게임 통계
        isInGame: false,
        currentGame: null,
        error: null
    };
    
    // 1. Riot ID로 PUUID 조회
    const accountUrl = `https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?api_key=${apiKey}`;
    
    const accountRes = await fetch(accountUrl);
    if (!accountRes.ok) {
        throw new Error(`계정 조회 실패: ${accountRes.status}`);
    }
    const accountData = await accountRes.json();
    data.puuid = accountData.puuid;
    
    // 2. 소환사 정보 조회
    const summonerUrl = `https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/${data.puuid}?api_key=${apiKey}`;
    
    const summonerRes = await fetch(summonerUrl);
    if (!summonerRes.ok) {
        throw new Error(`소환사 조회 실패: ${summonerRes.status}`);
    }
    const summonerData = await summonerRes.json();
    data.summoner = {
        id: summonerData.id,
        name: summonerData.name || gameName,
        level: summonerData.summonerLevel,
        profileIconId: summonerData.profileIconId,
        profileIconUrl: `https://ddragon.leagueoflegends.com/cdn/${champions.version || '14.24.1'}/img/profileicon/${summonerData.profileIconId}.png`
    };
    
    // 3. 랭크 정보 조회
    const leagueUrl = `https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/${data.puuid}?api_key=${apiKey}`;
    
    const leagueRes = await fetch(leagueUrl);
    if (leagueRes.ok) {
        const leagueData = await leagueRes.json();
        
        const soloRank = leagueData.find(q => q.queueType === 'RANKED_SOLO_5x5');
        if (soloRank) {
            data.soloRank = {
                tier: soloRank.tier,
                rank: soloRank.rank,
                lp: soloRank.leaguePoints,
                wins: soloRank.wins,
                losses: soloRank.losses,
                winRate: Math.round((soloRank.wins / (soloRank.wins + soloRank.losses)) * 100)
            };
        } else {
            data.soloRank = { tier: 'UNRANKED', rank: '', lp: 0, wins: 0, losses: 0, winRate: 0 };
        }
        
        const flexRank = leagueData.find(q => q.queueType === 'RANKED_FLEX_SR');
        if (flexRank) {
            data.flexRank = {
                tier: flexRank.tier,
                rank: flexRank.rank,
                lp: flexRank.leaguePoints,
                wins: flexRank.wins,
                losses: flexRank.losses,
                winRate: Math.round((flexRank.wins / (flexRank.wins + flexRank.losses)) * 100)
            };
        } else {
            data.flexRank = { tier: 'UNRANKED', rank: '', lp: 0, wins: 0, losses: 0, winRate: 0 };
        }
    } else {
        data.soloRank = { tier: 'UNRANKED', rank: '', lp: 0, wins: 0, losses: 0, winRate: 0 };
        data.flexRank = { tier: 'UNRANKED', rank: '', lp: 0, wins: 0, losses: 0, winRate: 0 };
    }
    
    // 4. 챔피언 숙련도 조회 (상위 5개)
    const masteryUrl = `https://kr.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/${data.puuid}/top?count=5&api_key=${apiKey}`;
    
    const masteryRes = await fetch(masteryUrl);
    if (masteryRes.ok) {
        const masteryData = await masteryRes.json();
        data.topChampions = masteryData.map(m => {
            const champ = champions[m.championId] || {};
            return {
                championId: m.championId,
                championName: champ.name || `Champion ${m.championId}`,
                championImage: champ.image || '',
                level: m.championLevel,
                points: m.championPoints
            };
        });
    }
    
    // 5. 최근 20게임 전적 조회
    const matchListUrl = `https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/${data.puuid}/ids?start=0&count=20&api_key=${apiKey}`;
    
    const matchListRes = await fetch(matchListUrl);
    if (matchListRes.ok) {
        const matchIds = await matchListRes.json();
        
        // 최근 10게임 상세 조회 (표시용)
        const matchPromises = matchIds.slice(0, 10).map(async (matchId) => {
            try {
                const matchUrl = `https://asia.api.riotgames.com/lol/match/v5/matches/${matchId}?api_key=${apiKey}`;
                const matchRes = await fetch(matchUrl);
                if (!matchRes.ok) return null;
                
                const matchData = await matchRes.json();
                const participant = matchData.info.participants.find(p => p.puuid === data.puuid);
                
                if (!participant) return null;
                
                const champ = champions[participant.championId] || {};
                
                return {
                    matchId: matchId,
                    gameMode: matchData.info.gameMode,
                    queueId: matchData.info.queueId,
                    gameDuration: Math.floor(matchData.info.gameDuration / 60),
                    gameEndTimestamp: matchData.info.gameEndTimestamp,
                    win: participant.win,
                    championId: participant.championId,
                    championName: champ.name || participant.championName,
                    championImage: champ.image || '',
                    kills: participant.kills,
                    deaths: participant.deaths,
                    assists: participant.assists,
                    kda: participant.deaths === 0 ? 'Perfect' : ((participant.kills + participant.assists) / participant.deaths).toFixed(2),
                    cs: participant.totalMinionsKilled + participant.neutralMinionsKilled,
                    visionScore: participant.visionScore
                };
            } catch (e) {
                return null;
            }
        });
        
        const matches = await Promise.all(matchPromises);
        data.recentMatches = matches.filter(m => m !== null);
        
        // 최근 게임 통계 계산
        if (data.recentMatches.length > 0) {
            const wins = data.recentMatches.filter(m => m.win).length;
            const losses = data.recentMatches.length - wins;
            const totalKills = data.recentMatches.reduce((sum, m) => sum + m.kills, 0);
            const totalDeaths = data.recentMatches.reduce((sum, m) => sum + m.deaths, 0);
            const totalAssists = data.recentMatches.reduce((sum, m) => sum + m.assists, 0);
            
            data.recentStats = {
                games: data.recentMatches.length,
                wins: wins,
                losses: losses,
                winRate: Math.round((wins / data.recentMatches.length) * 100),
                avgKills: (totalKills / data.recentMatches.length).toFixed(1),
                avgDeaths: (totalDeaths / data.recentMatches.length).toFixed(1),
                avgAssists: (totalAssists / data.recentMatches.length).toFixed(1),
                avgKDA: totalDeaths === 0 ? 'Perfect' : ((totalKills + totalAssists) / totalDeaths).toFixed(2)
            };
        }
    }
    
    // 6. 현재 게임 중인지 확인
    const spectatorUrl = `https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/${data.puuid}?api_key=${apiKey}`;
    
    const spectatorRes = await fetch(spectatorUrl);
    if (spectatorRes.ok) {
        const spectatorData = await spectatorRes.json();
        data.isInGame = true;
        
        const currentPlayer = spectatorData.participants.find(p => p.puuid === data.puuid);
        const champ = currentPlayer ? (champions[currentPlayer.championId] || {}) : {};
        
        data.currentGame = {
            gameId: spectatorData.gameId,
            gameMode: spectatorData.gameMode,
            gameType: spectatorData.gameType,
            gameStartTime: spectatorData.gameStartTime,
            gameLength: spectatorData.gameLength,
            championId: currentPlayer?.championId,
            championName: champ.name || `Champion ${currentPlayer?.championId}`,
            championImage: champ.image || '',
            teamId: currentPlayer?.teamId
        };
    } else {
        data.isInGame = false;
        data.currentGame = null;
    }
    
    return data;
}
