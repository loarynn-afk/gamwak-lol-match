// Vercel Serverless Function - Riot API 호출 (풀버전)
// 사용법: /api/player?name=단바오&tag=owo

// 챔피언 ID → 이름 매핑 (Data Dragon에서 가져옴)
let championData = null;

async function getChampionData() {
    if (championData) return championData;
    
    try {
        // 최신 버전 확인
        const versionRes = await fetch('https://ddragon.leagueoflegends.com/api/versions.json');
        const versions = await versionRes.json();
        const latestVersion = versions[0];
        
        // 챔피언 데이터 가져오기
        const champRes = await fetch(`https://ddragon.leagueoflegends.com/cdn/${latestVersion}/data/ko_KR/champion.json`);
        const champJson = await champRes.json();
        
        // ID → 이름 매핑 생성
        championData = {};
        for (const [key, value] of Object.entries(champJson.data)) {
            championData[value.key] = {
                id: key,
                name: value.name,
                image: `https://ddragon.leagueoflegends.com/cdn/${latestVersion}/img/champion/${value.image.full}`
            };
        }
        return championData;
    } catch (e) {
        return {};
    }
}

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
    // 챔피언 데이터 미리 로드
    const champions = await getChampionData();
    
    const data = {
        riotId: `${gameName}#${tagLine}`,
        puuid: null,
        summoner: null,
        soloRank: null,      // 솔로랭크
        flexRank: null,      // 자유랭크
        topChampions: [],    // 모스트 챔피언
        recentMatches: [],   // 최근 전적
        isInGame: false,     // 현재 게임 중 여부
        currentGame: null,   // 현재 게임 정보
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
        profileIconUrl: `https://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/${summonerData.profileIconId}.png`
    };
    
    // 3. 랭크 정보 조회 (솔로랭크 + 자유랭크)
    const leagueUrl = `https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/${data.puuid}?api_key=${apiKey}`;
    
    const leagueRes = await fetch(leagueUrl);
    if (leagueRes.ok) {
        const leagueData = await leagueRes.json();
        
        // 솔로랭크
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
        
        // 자유랭크
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
    
    // 5. 최근 전적 조회 (최근 10게임)
    const matchListUrl = `https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/${data.puuid}/ids?start=0&count=10&api_key=${apiKey}`;
    
    const matchListRes = await fetch(matchListUrl);
    if (matchListRes.ok) {
        const matchIds = await matchListRes.json();
        
        // 최근 5게임만 상세 조회 (API 호출 제한 고려)
        const matchPromises = matchIds.slice(0, 5).map(async (matchId) => {
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
                    gameDuration: Math.floor(matchData.info.gameDuration / 60), // 분 단위
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
                    visionScore: participant.visionScore,
                    items: [
                        participant.item0,
                        participant.item1,
                        participant.item2,
                        participant.item3,
                        participant.item4,
                        participant.item5,
                        participant.item6
                    ]
                };
            } catch (e) {
                return null;
            }
        });
        
        const matches = await Promise.all(matchPromises);
        data.recentMatches = matches.filter(m => m !== null);
    }
    
    // 6. 현재 게임 중인지 확인 (Spectator-V5)
    const spectatorUrl = `https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/${data.puuid}?api_key=${apiKey}`;
    
    const spectatorRes = await fetch(spectatorUrl);
    if (spectatorRes.ok) {
        const spectatorData = await spectatorRes.json();
        data.isInGame = true;
        
        // 현재 게임 정보
        const currentPlayer = spectatorData.participants.find(p => p.puuid === data.puuid);
        const champ = currentPlayer ? (champions[currentPlayer.championId] || {}) : {};
        
        data.currentGame = {
            gameId: spectatorData.gameId,
            gameMode: spectatorData.gameMode,
            gameType: spectatorData.gameType,
            gameStartTime: spectatorData.gameStartTime,
            gameLength: spectatorData.gameLength, // 초 단위
            championId: currentPlayer?.championId,
            championName: champ.name || `Champion ${currentPlayer?.championId}`,
            teamId: currentPlayer?.teamId
        };
    } else {
        data.isInGame = false;
        data.currentGame = null;
    }
    
    return data;
}
