import React, { useState, useEffect } from 'react';
import {
  createEmptyBoard,
  dropPiece,
  checkWin,
  getValidLocations,
  isTerminalNode,
  minimax,
  PLAYER_1,
  PLAYER_2,
  CPU,
  EMPTY,
  ROWS,
  COLS
} from './logic';

function App() {
  const [board, setBoard] = useState(createEmptyBoard());
  const [currentPlayer, setCurrentPlayer] = useState(PLAYER_1);
  const [winner, setWinner] = useState(null);
  const [isDraw, setIsDraw] = useState(false);
  const [playWithCPU, setPlayWithCPU] = useState(true); // Default to CPU
  const [isCPUThinking, setIsCPUThinking] = useState(false);

  // Reinicia o jogo
  const resetGame = () => {
    setBoard(createEmptyBoard());
    setCurrentPlayer(PLAYER_1);
    setWinner(null);
    setIsDraw(false);
    setIsCPUThinking(false);
  };

  // Muda o modo de jogo
  const toggleGameMode = (modeCPU) => {
    setPlayWithCPU(modeCPU);
    resetGame();
  };

  // Jogada do computador (Minimax)
  useEffect(() => {
    if (playWithCPU && currentPlayer === CPU && !winner && !isDraw) {
      setIsCPUThinking(true);
      // Timeout para dar a sensação de que o computador está "pensando" e evitar bloquear a UI
      const timer = setTimeout(() => {
        const { column } = minimax(board, 5, -Infinity, Infinity, true); // Profundidade 5
        if (column !== null) {
          handleColumnClick(column, true);
        }
        setIsCPUThinking(false);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [currentPlayer, playWithCPU, winner, isDraw, board]);

  const handleColumnClick = (col, isCPUPlay = false) => {
    if (winner || isDraw || (isCPUThinking && !isCPUPlay)) return;

    // Cópia profunda do tabuleiro
    const newBoard = board.map(row => [...row]);

    const rowIdx = dropPiece(newBoard, col, currentPlayer);

    // Se a coluna estiver cheia (rowIdx === -1), não faz nada
    if (rowIdx === -1) return;

    setBoard(newBoard);

    if (checkWin(newBoard, currentPlayer)) {
      setWinner(currentPlayer);
    } else if (getValidLocations(newBoard).length === 0) {
      setIsDraw(true);
    } else {
      setCurrentPlayer(currentPlayer === PLAYER_1 ? PLAYER_2 : PLAYER_1);
    }
  };

  return (
    <>

      <h1>Ligue 4</h1>

      <div className="controls">
        <button
          className={!playWithCPU ? 'active-mode' : ''}
          onClick={() => toggleGameMode(false)}
        >
          2 Jogadores
        </button>
        <button
          className={playWithCPU ? 'active-mode' : ''}
          onClick={() => toggleGameMode(true)}
        >
          1 Jogador (vs CPU)
        </button>
        <button onClick={resetGame} style={{marginLeft: '15px'}}>
          Reiniciar Jogo
        </button>
      </div>

      <div className="status">
        {winner ? (
          <span style={{ color: winner === PLAYER_1 ? '#ef4444' : '#3b82f6' }}>
            Vitória do Jogador {winner === PLAYER_1 ? '1 (Vermelho)' : '2 (Azul)'}!
          </span>
        ) : isDraw ? (
          <span>Empate! O tabuleiro está cheio.</span>
        ) : (
          <span>
            Vez do{' '}
            <span style={{ color: currentPlayer === PLAYER_1 ? '#ef4444' : '#3b82f6' }}>
              {currentPlayer === PLAYER_1 ? 'Jogador 1 (Vermelho)' : playWithCPU ? 'Computador (Azul)' : 'Jogador 2 (Azul)'}
            </span>
            {isCPUThinking && ' (Pensando...)'}
          </span>
        )}
      </div>

      <div className="board-container">
        <div className="board">
          {board.map((row, rIdx) => (
            <div key={rIdx} className="row">
              {row.map((cell, cIdx) => (
                <div
                  key={`${rIdx}-${cIdx}`}
                  className="cell"
                  onClick={() => handleColumnClick(cIdx)}
                >
                  {cell !== EMPTY && (
                    <div className={`piece ${cell === PLAYER_1 ? 'player1' : 'player2'}`}></div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default App;
