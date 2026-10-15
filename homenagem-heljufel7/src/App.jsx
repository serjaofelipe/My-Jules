import React from 'react';
import Snow from './components/Snow';
import { Trophy, Crosshair, TrendingUp, Skull, Shield, History, Award } from 'lucide-react';
import './index.css'; // Will overwrite with tailwind-like custom styles

export default function App() {
  const player = {
    name: 'Heljufel7',
    tag: '#BR1',
    icon: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/profileicon/53.png',
    elo: 'Esmeralda II',
    lp: 42,
    winrate: '54%',
  };

  const mainChampion = {
    name: 'Ashe',
    title: 'a Arqueira de Gelo',
    image: 'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Ashe_0.jpg',
    square: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/champion/Ashe.png',
    masteryScore: '1,245,600',
    masteryLevel: 7,
  };

  const recentMatches = [
    { result: 'Vitória', kda: '12 / 2 / 8', cs: 210, duration: '28:45', champ: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/champion/Ashe.png' },
    { result: 'Vitória', kda: '8 / 4 / 15', cs: 195, duration: '25:20', champ: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/champion/Ashe.png' },
    { result: 'Derrota', kda: '5 / 6 / 10', cs: 230, duration: '35:10', champ: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/champion/Ashe.png' },
    { result: 'Vitória', kda: '15 / 1 / 9', cs: 180, duration: '22:15', champ: 'https://ddragon.leagueoflegends.com/cdn/14.8.1/img/champion/Ashe.png' },
  ];

  return (
    <div className="app-container">
      <Snow />

      {/* Background Overlay */}
      <div
        className="background-image"
        style={{ backgroundImage: `url(${mainChampion.image})` }}
      >
        <div className="background-overlay"></div>
      </div>

      <div className="content-container">

        {/* Header Section */}
        <header className="header glass-panel">
          <div className="profile-section">
            <img src={player.icon} alt="Profile Icon" className="profile-icon" />
            <div className="profile-info">
              <h1 className="player-name">{player.name} <span className="player-tag">{player.tag}</span></h1>
              <div className="elo-badge">
                <Shield className="icon-small text-accent" />
                <span>{player.elo} - {player.lp} LP</span>
                <span className="winrate">({player.winrate} WR)</span>
              </div>
            </div>
          </div>
          <div className="tribute-badge">
            <Trophy className="icon-medium text-gold" />
            <span>Dossiê de Homenagem</span>
          </div>
        </header>

        <main className="main-grid">

          {/* Main Champion Card */}
          <section className="champion-card glass-panel flex-col-center">
            <h2 className="section-title">Campeão Principal</h2>
            <img src={mainChampion.square} alt={mainChampion.name} className="champion-square" />
            <h3 className="champion-name">{mainChampion.name}</h3>
            <p className="champion-title">{mainChampion.title}</p>

            <div className="mastery-info mt-4">
              <Award className="mastery-icon text-gold" size={60} />
              <div className="mastery-text">
                <p className="mastery-score-label">Pontuação de Maestria</p>
                <p className="mastery-score">{mainChampion.masteryScore} pts</p>
              </div>
            </div>
          </section>

          {/* Stats Overview */}
          <section className="stats-card glass-panel">
            <h2 className="section-title"><Crosshair className="icon-small inline mr-2"/> Desempenho (Últimas 20 Partidas)</h2>
            <div className="stats-grid">
              <div className="stat-item">
                <TrendingUp className="icon-large text-green" />
                <span className="stat-value text-green">65%</span>
                <span className="stat-label">Taxa de Vitória</span>
              </div>
              <div className="stat-item">
                <Skull className="icon-large text-blue" />
                <span className="stat-value">4.5:1</span>
                <span className="stat-label">KDA Médio</span>
              </div>
              <div className="stat-item">
                <Crosshair className="icon-large text-purple" />
                <span className="stat-value">7.8</span>
                <span className="stat-label">CS / min</span>
              </div>
            </div>
          </section>

          {/* Match History */}
          <section className="history-card glass-panel history-span">
            <h2 className="section-title"><History className="icon-small inline mr-2"/> Histórico Recente</h2>
            <div className="match-list">
              {recentMatches.map((match, idx) => (
                <div key={idx} className={`match-item ${match.result === 'Vitória' ? 'match-win' : 'match-loss'}`}>
                  <div className="match-champ">
                    <img src={match.champ} alt="Champion" />
                  </div>
                  <div className="match-details">
                    <span className={`match-result ${match.result === 'Vitória' ? 'text-green' : 'text-red'}`}>{match.result}</span>
                    <span className="match-duration">{match.duration}</span>
                  </div>
                  <div className="match-kda">
                    <span className="font-bold">{match.kda}</span>
                    <span className="match-cs">{match.cs} CS</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>

        <footer className="footer">
          <p>Homenagem ao jogador Heljufel7 - A flecha de cristal nunca erra.</p>
        </footer>
      </div>
    </div>
  );
}
