export const ROWS = 6;
export const COLS = 7;

export const PLAYER_1 = 1; // Vermelho
export const PLAYER_2 = 2; // Azul
export const CPU = 2;
export const EMPTY = 0;

export function createEmptyBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(EMPTY));
}

export function dropPiece(board, col, player) {
  for (let r = ROWS - 1; r >= 0; r--) {
    if (board[r][col] === EMPTY) {
      board[r][col] = player;
      return r;
    }
  }
  return -1; // Column full
}

export function isValidLocation(board, col) {
  return board[0][col] === EMPTY;
}

export function getValidLocations(board) {
  const validLocations = [];
  for (let c = 0; c < COLS; c++) {
    if (isValidLocation(board, c)) {
      validLocations.push(c);
    }
  }
  return validLocations;
}

export function checkWin(board, player) {
  // Horizontal
  for (let c = 0; c < COLS - 3; c++) {
    for (let r = 0; r < ROWS; r++) {
      if (
        board[r][c] === player &&
        board[r][c + 1] === player &&
        board[r][c + 2] === player &&
        board[r][c + 3] === player
      ) {
        return true;
      }
    }
  }
  // Vertical
  for (let c = 0; c < COLS; c++) {
    for (let r = 0; r < ROWS - 3; r++) {
      if (
        board[r][c] === player &&
        board[r + 1][c] === player &&
        board[r + 2][c] === player &&
        board[r + 3][c] === player
      ) {
        return true;
      }
    }
  }
  // Positively sloped diagonals
  for (let c = 0; c < COLS - 3; c++) {
    for (let r = 0; r < ROWS - 3; r++) {
      if (
        board[r][c] === player &&
        board[r + 1][c + 1] === player &&
        board[r + 2][c + 2] === player &&
        board[r + 3][c + 3] === player
      ) {
        return true;
      }
    }
  }
  // Negatively sloped diagonals
  for (let c = 0; c < COLS - 3; c++) {
    for (let r = 3; r < ROWS; r++) {
      if (
        board[r][c] === player &&
        board[r - 1][c + 1] === player &&
        board[r - 2][c + 2] === player &&
        board[r - 3][c + 3] === player
      ) {
        return true;
      }
    }
  }
  return false;
}

export function isTerminalNode(board) {
  return checkWin(board, PLAYER_1) || checkWin(board, PLAYER_2) || getValidLocations(board).length === 0;
}

function evaluateWindow(window, player) {
  let score = 0;
  const oppPlayer = player === PLAYER_1 ? PLAYER_2 : PLAYER_1;

  let playerCount = 0;
  let emptyCount = 0;
  let oppCount = 0;

  for (const cell of window) {
    if (cell === player) playerCount++;
    else if (cell === EMPTY) emptyCount++;
    else if (cell === oppPlayer) oppCount++;
  }

  if (playerCount === 4) {
    score += 100;
  } else if (playerCount === 3 && emptyCount === 1) {
    score += 5;
  } else if (playerCount === 2 && emptyCount === 2) {
    score += 2;
  }

  if (oppCount === 3 && emptyCount === 1) {
    score -= 4;
  }

  return score;
}

export function scorePosition(board, player) {
  let score = 0;

  // Center column preference
  let centerArray = [];
  for (let r = 0; r < ROWS; r++) {
    centerArray.push(board[r][Math.floor(COLS / 2)]);
  }
  let centerCount = centerArray.filter((cell) => cell === player).length;
  score += centerCount * 3;

  // Horizontal
  for (let r = 0; r < ROWS; r++) {
    let rowArray = board[r];
    for (let c = 0; c < COLS - 3; c++) {
      let window = rowArray.slice(c, c + 4);
      score += evaluateWindow(window, player);
    }
  }

  // Vertical
  for (let c = 0; c < COLS; c++) {
    let colArray = [];
    for (let r = 0; r < ROWS; r++) {
      colArray.push(board[r][c]);
    }
    for (let r = 0; r < ROWS - 3; r++) {
      let window = colArray.slice(r, r + 4);
      score += evaluateWindow(window, player);
    }
  }

  // Positive Diagonal
  for (let r = 0; r < ROWS - 3; r++) {
    for (let c = 0; c < COLS - 3; c++) {
      let window = [board[r][c], board[r + 1][c + 1], board[r + 2][c + 2], board[r + 3][c + 3]];
      score += evaluateWindow(window, player);
    }
  }

  // Negative Diagonal
  for (let r = 0; r < ROWS - 3; r++) {
    for (let c = 0; c < COLS - 3; c++) {
      let window = [board[r + 3][c], board[r + 2][c + 1], board[r + 1][c + 2], board[r][c + 3]];
      score += evaluateWindow(window, player);
    }
  }

  return score;
}

export function minimax(board, depth, alpha, beta, maximizingPlayer) {
  const validLocations = getValidLocations(board);
  const isTerminal = isTerminalNode(board);

  if (depth === 0 || isTerminal) {
    if (isTerminal) {
      if (checkWin(board, CPU)) {
        return { column: null, score: 100000000000000 };
      } else if (checkWin(board, PLAYER_1)) {
        return { column: null, score: -10000000000000 };
      } else {
        return { column: null, score: 0 };
      }
    } else {
      return { column: null, score: scorePosition(board, CPU) };
    }
  }

  if (maximizingPlayer) {
    let value = -Infinity;
    let bestCol = validLocations[Math.floor(Math.random() * validLocations.length)];
    for (let col of validLocations) {
      let bCopy = board.map((row) => [...row]);
      dropPiece(bCopy, col, CPU);
      let newScore = minimax(bCopy, depth - 1, alpha, beta, false).score;
      if (newScore > value) {
        value = newScore;
        bestCol = col;
      }
      alpha = Math.max(alpha, value);
      if (alpha >= beta) {
        break;
      }
    }
    return { column: bestCol, score: value };
  } else {
    let value = Infinity;
    let bestCol = validLocations[Math.floor(Math.random() * validLocations.length)];
    for (let col of validLocations) {
      let bCopy = board.map((row) => [...row]);
      dropPiece(bCopy, col, PLAYER_1);
      let newScore = minimax(bCopy, depth - 1, alpha, beta, true).score;
      if (newScore < value) {
        value = newScore;
        bestCol = col;
      }
      beta = Math.min(beta, value);
      if (alpha >= beta) {
        break;
      }
    }
    return { column: bestCol, score: value };
  }
}
