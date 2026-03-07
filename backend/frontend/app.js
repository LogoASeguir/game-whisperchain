/* ============================================
   WHISPERCHAIN - MULTIPLAYER CLIENT

   Backend is SINGLE SOURCE OF TRUTH
   Frontend only DISPLAYS backend data
   ============================================ */

var API_BASE = '';

/* ============================================
   GLOBAL STATE
   ============================================ */
var socket = null;
var gameEndTimeout = null;  // NEW: Safety timeout tracker
var gameState = {
  roomCode: "",
  players: [],
  myUserId: null,
  currentRound: 0,
  totalRounds: 0,
  selectedWords: [],
  maxWords: 2,
  fillTemplate: [],
  blankPositions: [],
  currentBlankIndex: 0,
  chain: [],
  rounds: [],
  timerInterval: null,
  revealIndex: 0,
  isMyTurn: false
};

/* ============================================
   SOCKET CONNECTION
   ============================================ */
function connectSocket() {
  console.log("[SOCKET] Connecting...");

  if (!window.io) {
    console.error("[SOCKET] Socket.IO not loaded!");
    return;
  }

  socket = io(window.location.origin, {
    transports: ['polling', 'websocket'],
    upgrade: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    timeout: 20000
  });

  socket.on('connect', function() {
    console.log("[SOCKET] Connected:", socket.id);

    var userId = parseInt(sessionStorage.getItem('user_id'));
    gameState.myUserId = userId;

    if (userId) {
      socket.emit('auth', { user_id: userId });
    } else {
      console.log("[SOCKET] No user_id, redirecting to login");
      window.location.href = '/';
    }
  });

  socket.on('disconnect', function(reason) {
    console.log("[SOCKET] Disconnected:", reason);
    
    // If server kicked us out, redirect to lobby
    if (reason === 'io server disconnect') {
      console.log("[SOCKET] Server disconnect, redirecting to lobby");
      setTimeout(function() {
        sessionStorage.removeItem('current_room');
        window.location.href = '/lobby.html';
      }, 2000);
    }
  });

  socket.on('connect_error', function(error) {
    console.error("[SOCKET] Connection error:", error);
  });

  socket.on('error', function(data) {
    console.error("[SOCKET] Error:", data.msg || data);
    alert("Connection error: " + (data.msg || "Something went wrong"));
    
    // Redirect to lobby after error
    setTimeout(function() {
      sessionStorage.removeItem('current_room');
      window.location.href = '/lobby.html';
    }, 2000);
  });

  socket.on('authed', function(data) {
    console.log("[SOCKET] Authenticated as:", data.username);

    var roomCode = sessionStorage.getItem('current_room');
    if (roomCode) {
      socket.emit('join', { room: roomCode });
    }
  });

  socket.on('room_state', function(data) {
    console.log("[SOCKET] Room state:", data);
    gameState.roomCode = data.code;
    gameState.players = data.players;
    updateMySignalFromPlayers();
    renderPlayers();
  });

  socket.on('players', function(data) {
    console.log("[SOCKET] Players:", data.players.length);
    gameState.players = data.players;
    updateMySignalFromPlayers();
    renderPlayers();
  });

  socket.on('player_left', function(data) {
    console.log("[SOCKET] Player left");
    gameState.players = data.players;
    renderPlayers();
  });

  socket.on('left_game', function(data) {
    console.log("[SOCKET] Left game:", data.message);

    clearTimer();
    clearGameEndTimeout();  // NEW: Clear safety timeout

    sessionStorage.removeItem('current_room');

    setTimeout(function() {
      window.location.href = '/lobby.html';
    }, 100);
  });

  // NEW: Enhanced room_reset handler
  socket.on('room_reset', function(data) {
    console.log("[SOCKET] Room reset to waiting state");

    clearTimer();
    clearGameEndTimeout();  // NEW: Clear safety timeout

    gameState.roomCode = data.code;
    gameState.players = data.players;
    gameState.currentRound = 0;
    gameState.totalRounds = 0;
    gameState.rounds = [];
    gameState.chain = [];
    gameState.isMyTurn = false;

    showScene('waiting');
    renderPlayers();

    var btn = document.getElementById('ready-btn');
    if (btn) {
      btn.classList.remove('is-ready');
      btn.textContent = 'READY';
    }

    updateReadyBar(0);
  });

  socket.on('ready_update', function(data) {
    console.log("[SOCKET] Ready:", data.ready_pct.toFixed(0) + "%");
    gameState.players = data.players;
    renderPlayers();
    updateReadyBar(data.ready_pct);
  });

  socket.on('countdown', function(data) {
    console.log("[SOCKET] Countdown:", data.seconds);
    showStartingCountdown(data.seconds);
  });

  socket.on('game_start', function(data) {
    console.log("[SOCKET] Game start!");
    gameState.players = data.players;
    gameState.totalRounds = data.total_rounds;
    gameState.isMyTurn = false;
    showScene('countdown');
    startGameCountdown(3);
  });

  socket.on('round_start', function(data) {
    console.log("[SOCKET] Round start:", data);
    gameState.currentRound = data.round;
    gameState.totalRounds = data.total_rounds;
    gameState.maxWords = data.max_words;
    gameState.isMyTurn = false;
    updateRoundDisplay();

    var myUserId = parseInt(sessionStorage.getItem('user_id'));

    if (data.picker_user_id === myUserId) {
      console.log("[SOCKET] I am the picker!");
      gameState.isMyTurn = true;
      showPickingScene(data.word_options);
    } else {
      console.log("[SOCKET] Waiting for:", data.picker);
      showWaitingScene(data.picker, "is choosing words", 15);
    }
  });

  socket.on('words_submitted', function(data) {
    console.log("[SOCKET] Words:", data.message);
    if (!gameState.isMyTurn) {
      showPassedScene();
    }
  });

  socket.on('your_turn', function(data) {
    console.log("[SOCKET] MY TURN TO TYPE");
    console.log("[SOCKET] Message:", data.message);
    console.log("[SOCKET] Signal:", data.signal);
    console.log("[SOCKET] Time:", data.time);

    gameState.isMyTurn = true;
    clearTimer();
    showFillBlanksScene(data.message, data.signal, data.time || 15);
  });

  socket.on('player_typing', function(data) {
    console.log("[SOCKET] Other player typing:", data.username);

    if (!gameState.isMyTurn) {
      showWaitingScene(data.username, "is typing", data.time || 15);
    }
  });

  socket.on('player_done', function(data) {
    console.log("[SOCKET] Player done:", data.username);
    if (!gameState.isMyTurn) {
      showPassedScene();
    }
  });

  socket.on('round_end', function(data) {
    console.log("[SOCKET] Round end");
    gameState.chain = data.round_data.chain;
    gameState.players = data.players;
    gameState.rounds.push(data.round_data);
    gameState.isMyTurn = false;
    updateMySignalFromPlayers();
    startReveal();
  });

  socket.on('vote_update', function(data) {
    console.log("[SOCKET] Votes:", data.votes + "/" + data.total);
    var el = document.getElementById('vote-count');
    if (el) el.textContent = data.votes + "/" + data.total + " voted";
  });

  // NEW: Enhanced game_end handler with safety timeout
  socket.on('game_end', function(data) {
    console.log("[SOCKET] Game end!");
    console.log("[SOCKET] game_id:", data.game_id);
    console.log("[SOCKET] Rankings:", data.rankings);

    // Clear any existing timeout
    clearGameEndTimeout();

    gameState.isMyTurn = false;
    updateMySignalFromRankings(data.rankings);

    showGameOver(data.rankings, data.rounds, data.num_players);

    // NEW: Safety timeout - auto-redirect if user doesn't interact
    gameEndTimeout = setTimeout(function() {
      console.log("[SAFETY] Auto-redirecting to lobby after 30 seconds");
      sessionStorage.removeItem('current_room');
      window.location.href = '/lobby.html';
    }, 30000);  // 30 seconds
  });
}

/* ============================================
   SAFETY HELPERS
   ============================================ */
function clearGameEndTimeout() {
  if (gameEndTimeout) {
    clearTimeout(gameEndTimeout);
    gameEndTimeout = null;
    console.log("[SAFETY] Cleared game end timeout");
  }
}

/* ============================================
   SIGNAL SYNC (Backend -> SessionStorage)
   ============================================ */
function updateMySignalFromPlayers() {
  var myUserId = parseInt(sessionStorage.getItem('user_id'));
  for (var i = 0; i < gameState.players.length; i++) {
    var p = gameState.players[i];
    if (p.user_id === myUserId) {
      var signal = p.signal || p.signal_strength || 50;
      sessionStorage.setItem('signal_strength', signal);
      console.log("[SYNC] Signal from players:", signal);
      break;
    }
  }
}

function updateMySignalFromRankings(rankings) {
  var myUserId = parseInt(sessionStorage.getItem('user_id'));
  for (var i = 0; i < rankings.length; i++) {
    var r = rankings[i];
    if (r.user_id === myUserId) {
      var signal = r.signal || r.signal_strength || 50;
      sessionStorage.setItem('signal_strength', signal);
      console.log("[SYNC] Signal from rankings:", signal);
      break;
    }
  }
}

/* ============================================
   SCENE MANAGEMENT
   ============================================ */
function showScene(sceneId) {
  console.log("[SCENE] ->", sceneId);

  var scenes = document.querySelectorAll('.scene');
  for (var i = 0; i < scenes.length; i++) {
    scenes[i].classList.remove('active');
  }

  var scene = document.getElementById('scene-' + sceneId);
  if (scene) {
    scene.classList.add('active');
  } else {
    console.error("[SCENE] Not found:", sceneId);
  }
}

/* ============================================
   TIMER
   ============================================ */
function clearTimer() {
  if (gameState.timerInterval) {
    clearInterval(gameState.timerInterval);
    gameState.timerInterval = null;
  }
}

function startTimer(elementId, seconds, callback) {
  console.log("[TIMER] Start:", elementId, seconds + "s");
  clearTimer();

  var el = document.getElementById(elementId);
  if (!el) {
    console.error("[TIMER] Element not found:", elementId);
    return;
  }

  var time = seconds;
  el.textContent = time;
  el.classList.remove('warning', 'critical');

  gameState.timerInterval = setInterval(function() {
    time--;
    el.textContent = time;

    if (time <= 3) {
      el.classList.add('critical');
    } else if (time <= 5) {
      el.classList.add('warning');
    }

    if (time <= 0) {
      clearTimer();
      if (callback) callback();
    }
  }, 1000);
}

/* ============================================
   PLAYERS
   ============================================ */
function renderPlayers() {
  var grid = document.getElementById('players-grid');
  if (!grid) return;

  var myUserId = parseInt(sessionStorage.getItem('user_id'));

  var html = '';
  for (var i = 0; i < gameState.players.length; i++) {
    var p = gameState.players[i];
    var isYou = p.user_id === myUserId;
    var signal = p.signal || p.signal_strength || 50;

    html += '<div class="player-bubble ' + (isYou ? 'you' : '') + ' ' + (p.ready ? 'ready' : '') + '">';
    html += '<span class="player-name">' + (isYou ? 'You' : p.username) + '</span>';
    html += '<span class="player-signal">' + signal + '%</span>';
    html += '<span class="player-status ' + (p.ready ? '' : 'not') + '">' + (p.ready ? 'READY' : 'NOT READY') + '</span>';
    html += '</div>';
  }
  grid.innerHTML = html;

  var total = gameState.players.length;
  var readyCount = 0;
  for (var i = 0; i < gameState.players.length; i++) {
    if (gameState.players[i].ready) readyCount++;
  }
  var pct = total > 0 ? (readyCount / total * 100) : 0;
  updateReadyBar(pct);
}

function updateReadyBar(pct) {
  var fill = document.getElementById('ready-fill');
  var text = document.getElementById('ready-text');

  if (fill) fill.style.width = pct + '%';
  if (text) text.textContent = Math.round(pct) + '% Ready (need 60%)';
}

function toggleReady() {
  console.log("[ACTION] Toggle ready");

  if (socket && socket.connected) {
    socket.emit('ready', {});
  }

  var btn = document.getElementById('ready-btn');
  if (btn) {
    btn.classList.toggle('is-ready');
    btn.textContent = btn.classList.contains('is-ready') ? 'READY!' : 'READY';
  }
}

/* ============================================
   COUNTDOWNS
   ============================================ */
function showStartingCountdown(seconds) {
  var msg = document.getElementById('starting-message');
  var el = document.getElementById('start-countdown');

  if (msg) msg.classList.remove('hidden');

  var time = seconds;
  if (el) el.textContent = time;

  var interval = setInterval(function() {
    time--;
    if (el) el.textContent = time;
    if (time <= 0) clearInterval(interval);
  }, 1000);
}

function startGameCountdown(seconds) {
  var el = document.getElementById('countdown-number');
  var time = seconds;
  if (el) el.textContent = time;

  var interval = setInterval(function() {
    time--;
    if (el) el.textContent = time;
    if (time <= 0) clearInterval(interval);
  }, 1000);
}

function updateRoundDisplay() {
  var roundNum = document.getElementById('round-number');
  if (roundNum) roundNum.textContent = gameState.currentRound;

  var badges = document.querySelectorAll('[id^="round-badge"]');
  for (var i = 0; i < badges.length; i++) {
    badges[i].textContent = 'ROUND ' + gameState.currentRound;
  }

  var wordCount = document.getElementById('word-count');
  if (wordCount) wordCount.textContent = gameState.maxWords;
}

/* ============================================
   WORD PICKING (Uses backend word_options)
   ============================================ */
function showPickingScene(wordOptions) {
  console.log("[PICKING] Showing scene");
  showScene('picking');
  renderWordGrid(wordOptions);
  startTimer('timer-pick', 15, autoSubmitWords);
}

function renderWordGrid(wordOptions) {
  var grid = document.getElementById('word-grid');
  if (!grid) return;

  var words = wordOptions || [];

  for (var i = words.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var temp = words[i];
    words[i] = words[j];
    words[j] = temp;
  }

  var html = '';
  for (var i = 0; i < words.length; i++) {
    html += '<button class="word-bubble" onclick="selectWord(this)">' + words[i] + '</button>';
  }
  grid.innerHTML = html;

  gameState.selectedWords = [];
  updateSelectedDisplay();
}

function selectWord(btn) {
  var word = btn.textContent;

  if (btn.classList.contains('selected')) {
    btn.classList.remove('selected');
    gameState.selectedWords = gameState.selectedWords.filter(function(w) { return w !== word; });
  } else if (gameState.selectedWords.length < gameState.maxWords) {
    btn.classList.add('selected');
    gameState.selectedWords.push(word);
  }

  updateSelectedDisplay();
}

function updateSelectedDisplay() {
  var container = document.getElementById('selected-bubbles');
  var btn = document.getElementById('send-btn');

  if (container) {
    if (gameState.selectedWords.length === 0) {
      container.innerHTML = '-';
    } else {
      var html = '';
      for (var i = 0; i < gameState.selectedWords.length; i++) {
        html += '<span class="word-bubble selected small">' + gameState.selectedWords[i] + '</span>';
      }
      container.innerHTML = html;
    }
  }

  if (btn) btn.disabled = gameState.selectedWords.length !== gameState.maxWords;
}

function autoSubmitWords() {
  var grid = document.getElementById('word-grid');
  var buttons = grid ? grid.querySelectorAll('.word-bubble:not(.selected)') : [];
  var i = 0;

  while (gameState.selectedWords.length < gameState.maxWords && i < buttons.length) {
    gameState.selectedWords.push(buttons[i].textContent);
    i++;
  }

  submitWords();
}

function submitWords() {
  clearTimer();
  console.log("[ACTION] Submit words:", gameState.selectedWords);

  gameState.isMyTurn = false;

  if (socket && socket.connected) {
    socket.emit('submit_words', { words: gameState.selectedWords });
    showPassedScene();
  }
}

/* ============================================
   FILL IN BLANKS SCENE
   ============================================ */
function showFillBlanksScene(message, signal, time) {
  console.log("[FILL] SHOWING FILL BLANKS");
  console.log("[FILL] Message:", message);
  console.log("[FILL] Signal:", signal);
  console.log("[FILL] Time:", time);

  showScene('yourturn');

  var signalEl = document.getElementById('your-signal');
  if (signalEl) signalEl.textContent = signal + '%';

  setupFillBlanks(message);
  renderFillBlanks();

  setTimeout(function() {
    var input = document.getElementById('hidden-input');
    if (input) {
      input.value = '';
      input.focus();
      console.log("[FILL] Input focused!");
    } else {
      console.error("[FILL] Hidden input not found!");
    }
  }, 300);

  startTimer('timer-turn', time, function() {
    console.log("[FILL] Time up! Auto-submitting...");
    submitTyping();
  });
}

function setupFillBlanks(message) {
  gameState.fillTemplate = [];
  gameState.blankPositions = [];
  gameState.currentBlankIndex = 0;

  if (!message) {
    console.error("[FILL] No message!");
    return;
  }

  var chars = message.split('');
  for (var i = 0; i < chars.length; i++) {
    var ch = chars[i];
    var isBlank = (ch === '_');

    gameState.fillTemplate.push({
      isBlank: isBlank,
      char: ch,
      filled: isBlank ? '' : ch
    });

    if (isBlank) {
      gameState.blankPositions.push(i);
    }
  }

  console.log("[FILL] Template:", gameState.fillTemplate.length, "chars,", gameState.blankPositions.length, "blanks");
}

function renderFillBlanks() {
  var container = document.getElementById('fill-display');
  if (!container) {
    console.error("[FILL] Container not found!");
    return;
  }

  var currentPos = gameState.blankPositions[gameState.currentBlankIndex];

  var html = '';
  for (var i = 0; i < gameState.fillTemplate.length; i++) {
    var item = gameState.fillTemplate[i];

    if (item.char === ' ') {
      html += '<span class="fill-char space">&nbsp;</span>';
    } else if (item.isBlank) {
      var isCurrent = (i === currentPos);
      var display = item.filled || '_';
      var classes = 'fill-char blank';
      if (item.filled) classes += ' filled';
      if (isCurrent) classes += ' current';
      html += '<span class="' + classes + '">' + display + '</span>';
    } else {
      html += '<span class="fill-char">' + item.char + '</span>';
    }
  }

  container.innerHTML = html;
}

function handleFillInput(e) {
  var key = e.key;

  if (!gameState.isMyTurn) return;

  if (key === 'Backspace') {
    e.preventDefault();

    var pos = gameState.blankPositions[gameState.currentBlankIndex];

    if (pos !== undefined && gameState.fillTemplate[pos] && gameState.fillTemplate[pos].filled) {
      gameState.fillTemplate[pos].filled = '';
    } else if (gameState.currentBlankIndex > 0) {
      gameState.currentBlankIndex--;
      var prevPos = gameState.blankPositions[gameState.currentBlankIndex];
      if (prevPos !== undefined) gameState.fillTemplate[prevPos].filled = '';
    }

    renderFillBlanks();
    return;
  }

  if (key === 'Enter') {
    e.preventDefault();
    submitTyping();
    return;
  }

  if (key.length === 1 && /[a-zA-Z]/.test(key)) {
    e.preventDefault();

    if (gameState.currentBlankIndex < gameState.blankPositions.length) {
      var pos = gameState.blankPositions[gameState.currentBlankIndex];
      gameState.fillTemplate[pos].filled = key.toLowerCase();

      if (gameState.currentBlankIndex < gameState.blankPositions.length - 1) {
        gameState.currentBlankIndex++;
      }
    }

    renderFillBlanks();
  }
}

function getFinalMessage() {
  var result = '';
  for (var i = 0; i < gameState.fillTemplate.length; i++) {
    var item = gameState.fillTemplate[i];
    if (item.char === ' ') {
      result += ' ';
    } else if (item.isBlank) {
      result += item.filled || '_';
    } else {
      result += item.char;
    }
  }
  console.log("[FILL] Final:", result);
  return result;
}

function submitTyping() {
  clearTimer();

  var message = getFinalMessage();
  console.log("[ACTION] Submit typing:", message);

  gameState.isMyTurn = false;

  if (socket && socket.connected) {
    socket.emit('submit_typing', { message: message });
    showPassedScene();
  }
}

/* ============================================
   WAITING SCENE
   ============================================ */
function showWaitingScene(name, action, time) {
  console.log("[WAITING]", name, action, time ? time + "s" : "");

  showScene('typing');

  var nameEl = document.getElementById('typing-player-name');
  if (nameEl) nameEl.textContent = name;

  var textEl = document.querySelector('.typing-text');
  if (textEl) textEl.innerHTML = action + '<span class="dots"></span>';

  if (time) {
    var timerEl = document.getElementById('timer-typing');
    if (timerEl) {
      clearTimer();
      var t = time;
      timerEl.textContent = t;

      gameState.timerInterval = setInterval(function() {
        t--;
        timerEl.textContent = t;
        if (t <= 0) {
          clearTimer();
        }
      }, 1000);
    }
  }
}

function showPassedScene() {
  console.log("[SCENE] Passed");
  showScene('passed');
}

/* ============================================
   REVEAL
   ============================================ */
function startReveal() {
  console.log("[REVEAL] Starting, chain length:", gameState.chain.length);
  gameState.revealIndex = 0;
  showNextReveal();
}

function showNextReveal() {
  if (gameState.revealIndex >= gameState.chain.length) {
    showRoundScores();
    return;
  }

  showScene('reveal');

  var step = gameState.chain[gameState.revealIndex];
  console.log("[REVEAL] Step:", gameState.revealIndex, step);

  var title = document.getElementById('reveal-title');
  var player = document.getElementById('reveal-player');
  var message = document.getElementById('reveal-message');
  var score = document.getElementById('reveal-score');

  var msg = step.message || step.typed || '???';

  if (step.is_picker) {
    if (title) title.textContent = 'ORIGINAL MESSAGE';
    if (score) score.classList.add('hidden');
  } else {
    if (title) title.textContent = step.player + ' TYPED';
    if (score) {
      var change = step.signal_change || 0;
      score.textContent = (change >= 0 ? '+' : '') + change + '%';
      score.className = 'reveal-score ' + (change >= 0 ? 'positive' : 'negative');
      score.classList.remove('hidden');
    }
  }

  if (player) player.textContent = step.player;
  if (message) message.textContent = '"' + msg + '"';

  gameState.revealIndex++;
  setTimeout(showNextReveal, 2500);
}

function showRoundScores() {
  showScene('scores');

  var title = document.getElementById('scores-title');
  if (title) title.textContent = 'ROUND ' + gameState.currentRound + ' SCORES';

  var scoresDiv = document.getElementById('round-scores');
  if (!scoresDiv) return;

  var myUserId = parseInt(sessionStorage.getItem('user_id'));

  var sortedPlayers = gameState.players.slice().sort(function(a, b) {
    var sigA = a.signal || a.signal_strength || 0;
    var sigB = b.signal || b.signal_strength || 0;
    return sigB - sigA;
  });

  var html = '';

  for (var i = 0; i < sortedPlayers.length; i++) {
    var p = sortedPlayers[i];
    var isYou = p.user_id === myUserId;
    var signal = p.signal || p.signal_strength || 50;

    var change = 0;
    for (var j = 0; j < gameState.chain.length; j++) {
      if (gameState.chain[j].user_id === p.user_id) {
        change = gameState.chain[j].signal_change || 0;
        break;
      }
    }

    html += '<div class="score-row ' + (isYou ? 'you' : '') + '">';
    html += '<span class="score-name">' + (isYou ? 'You' : p.username) + '</span>';
    html += '<span class="score-signal">' + signal + '%</span>';

    if (change === 0) {
      html += '<span class="score-change neutral">-</span>';
    } else {
      html += '<span class="score-change ' + (change >= 0 ? 'positive' : 'negative') + '">';
      html += (change >= 0 ? '+' : '') + change + '%';
      html += '</span>';
    }

    html += '</div>';
  }

  scoresDiv.innerHTML = html;

  setTimeout(function() {
    showStayOrLeavePrompt();
  }, 2000);
}

/* ============================================
   GAME OVER
   ============================================ */
function showGameOver(rankings, rounds, numPlayers) {
  showScene('gameover');

  console.log("[GAMEOVER] Received rankings:", rankings.length, "players");
  console.log("[GAMEOVER] Total players:", numPlayers);

  var scoreboard = document.getElementById('scoreboard');
  if (!scoreboard) return;

  var myUserId = parseInt(sessionStorage.getItem('user_id'));
  var medals = ['gold', 'silver', 'bronze'];

  var sortedRankings = rankings.slice().sort(function(a, b) {
    var sigA = a.signal || a.signal_strength || 0;
    var sigB = b.signal || b.signal_strength || 0;
    return sigB - sigA;
  });

  var html = '';
  for (var i = 0; i < sortedRankings.length; i++) {
    var r = sortedRankings[i];
    var isYou = r.user_id === myUserId;
    var medal = medals[i] || '';
    var signal = r.signal || r.signal_strength || 50;

    html += '<div class="score-bubble ' + medal + ' ' + (isYou ? 'you' : '') + '">';
    html += '<span class="score-rank">#' + (i + 1) + '</span>';
    html += '<span class="score-name">' + (isYou ? 'You' : r.username) + '</span>';
    html += '<span class="score-signal">' + signal + '%</span>';
    html += '</div>';
  }

  scoreboard.innerHTML = html;
}

/* ============================================
   STAY OR LEAVE PROMPT
   ============================================ */
function showStayOrLeavePrompt() {
  console.log("[PROMPT] Showing stay/leave modal");

  var modal = document.getElementById('stay-modal');
  if (modal) {
    modal.classList.remove('hidden');
  }

  startTimer('timer-stay', 7, function() {
    console.log("[PROMPT] Timeout - auto-staying");
    stayInGame();
  });
}

function stayInGame() {
  console.log("[ACTION] Player chose to STAY");

  clearTimer();

  var modal = document.getElementById('stay-modal');
  if (modal) modal.classList.add('hidden');

  if (socket && socket.connected) {
    socket.emit('vote', { vote: 'yes' });
  }
}

function leaveGame() {
  console.log("[ACTION] Player chose to LEAVE");

  clearTimer();
  clearGameEndTimeout();  // NEW: Clear safety timeout when leaving

  var modal = document.getElementById('stay-modal');
  if (modal) modal.classList.add('hidden');

  if (socket && socket.connected) {
    socket.emit('vote', { vote: 'no' });
  }
}

/* ============================================
   LOGIN
   ============================================ */
function login() {
  var input = document.getElementById('username');
  if (!input) return;

  var username = input.value.trim();

  if (username.length < 3) {
    alert('Username must be at least 3 characters');
    return;
  }

  if (username.length > 20) {
    alert('Username too long');
    return;
  }

  sessionStorage.clear();

  fetch(API_BASE + '/api/user', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: username })
  })
  .then(function(res) {
    return res.json().then(function(data) {
      return { status: res.status, data: data };
    });
  })
  .then(function(result) {
    if (result.status >= 400) {
      alert(result.data.error || 'Error');
      return;
    }

    sessionStorage.setItem('username', result.data.username);
    sessionStorage.setItem('user_id', result.data.id);
    sessionStorage.setItem('signal_strength', result.data.signal_strength);

    window.location.href = '/lobby.html';
  })
  .catch(function(err) {
    console.error('[LOGIN] Error:', err);
    alert('Server error!');
  });
}

/* ============================================
   LOBBY
   ============================================ */
function loadUserInfo() {
  var username = sessionStorage.getItem('username') || 'Guest';
  var signal = sessionStorage.getItem('signal_strength');

  if (!signal || signal === 'undefined' || signal === 'null') {
    signal = '50';
  }

  var uEl = document.querySelector('.username');
  var sEl = document.querySelector('.signal');

  if (uEl) uEl.textContent = username;
  if (sEl) sEl.textContent = signal + '%';
}

function loadRooms() {
  var roomList = document.querySelector('.room-list');
  var noRooms = document.querySelector('.no-rooms');

  if (!roomList) return;

  fetch(API_BASE + '/api/rooms')
    .then(function(res) { return res.json(); })
    .then(function(rooms) {
      if (!rooms || rooms.length === 0) {
        roomList.innerHTML = '';
        if (noRooms) noRooms.classList.remove('hidden');
        return;
      }

      if (noRooms) noRooms.classList.add('hidden');

      var html = '';
      for (var i = 0; i < rooms.length; i++) {
        var room = rooms[i];
        var disabled = (room.players >= room.max_players || room.status !== 'waiting') ? 'disabled' : '';

        html += '<div class="room-card">';
        html += '<div class="room-left">';
        html += '<span class="room-code">' + room.code + '</span>';
        html += '<div class="room-details"><span class="room-players">' + room.players + '/' + room.max_players + '</span></div>';
        html += '</div>';
        html += '<button class="btn btn-tiny btn-join" onclick="joinRoom(\'' + room.code + '\')" ' + disabled + '>JOIN</button>';
        html += '</div>';
      }

      roomList.innerHTML = html;
    })
    .catch(function() {
      roomList.innerHTML = '';
      if (noRooms) noRooms.classList.remove('hidden');
    });
}

function createRoom() {
  fetch(API_BASE + '/api/rooms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}'
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    sessionStorage.setItem('current_room', data.code);
    window.location.href = '/room.html';
  })
  .catch(function() {
    alert('Could not create room');
  });
}

function joinRoom(code) {
  sessionStorage.setItem('current_room', code);
  window.location.href = '/room.html';
}

/* ============================================
   HISTORY
   ============================================ */
function loadHistory() {
  var list = document.getElementById('history-list');
  var noHistory = document.getElementById('no-history');

  if (!list) return;

  var userId = sessionStorage.getItem('user_id');

  console.log("[HISTORY] Loading for user_id:", userId);

  if (!userId) {
    list.innerHTML = '';
    if (noHistory) noHistory.classList.remove('hidden');
    return;
  }

  var url = API_BASE + '/api/history?user_id=' + encodeURIComponent(userId);

  fetch(url)
    .then(function(res) { return res.json(); })
    .then(function(games) {
      console.log("[HISTORY] Got games:", games.length);

      if (!games || games.length === 0) {
        list.innerHTML = '';
        if (noHistory) noHistory.classList.remove('hidden');
        return;
      }

      if (noHistory) noHistory.classList.add('hidden');

      var html = '';
      for (var i = 0; i < games.length; i++) {
        var game = games[i];

        html += '<div class="history-card">';
        html += '<div class="history-header">';
        html += '<span class="history-room">' + (game.room_code || '???') + '</span>';
        html += '<span>' + (game.num_players || '?') + ' players</span>';
        html += '</div>';

        var rounds = game.rounds || [];
        if (rounds.length > 0) {
          html += '<div class="history-rounds">';

          for (var j = 0; j < rounds.length; j++) {
            var round = rounds[j];
            var chain = round.chain || [];

            html += '<div class="round-chain">';
            html += '<span class="round-label">Round ' + (round.round || (j + 1)) + ':</span> ';

            if (chain.length > 0) {
              var chainParts = [];
              for (var k = 0; k < chain.length; k++) {
                var msg = chain[k].message || chain[k].typed || '???';
                chainParts.push('"' + msg + '"');
              }
              html += chainParts.join(' → ');
          } else {
              html += '"' + (round.original || '?') + '" → "' + (round.final || '?') + '"';
            }

            html += '</div>';
          }

          html += '</div>';
        } else {
          html += '<div class="history-rounds"><p class="no-rounds">No round data</p></div>';
        }

        html += '</div>';
      }

      list.innerHTML = html;
    })
    .catch(function(err) {
      console.error("[HISTORY] Error:", err);
      list.innerHTML = '<p>Error loading history</p>
      if (noHistory) noHistory.classList.remove('hidden');
    });
}

/* ============================================
   NAVIGATION
   ============================================ */
function goToLobby() {
  clearTimer();
  clearGameEndTimeout();  // NEW: Clear safety timeout

  if (socket && socket.connected) {
    socket.emit('leave', {});
  }

  sessionStorage.removeItem('current_room');
  window.location.href = '/lobby.html';
}

function goToHistory() {
  window.location.href = '/history.html';
}

function leaveRoom() {
  var modal = document.getElementById('leave-modal');
  if (modal) modal.classList.remove('hidden');
}

function confirmLeave() {
  goToLobby();
}

function closeModal() {
  var modal = document.getElementById('leave-modal');
  if (modal) modal.classList.add('hidden');
}

/* ============================================
   INITIALIZATION
   ============================================ */
document.addEventListener('DOMContentLoaded', function() {
  console.log('[INIT] Page:', window.location.pathname);

  var usernameInput = document.getElementById('username');
  if (usernameInput) {
    usernameInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') login();
    });
  }

  loadUserInfo();
  if (document.querySelector('.room-list')) {
    loadRooms();
    setInterval(loadRooms, 5000);
  }

  var roomCode = sessionStorage.getItem('current_room');
  var roomCodeEl = document.getElementById('room-code');
  if (roomCodeEl && roomCode) {
    roomCodeEl.textContent = roomCode;
    gameState.roomCode = roomCode;
  }

  if (document.getElementById('players-grid') && roomCode) {
    gameState.myUserId = parseInt(sessionStorage.getItem('user_id'));
    connectSocket();
  }

  var hiddenInput = document.getElementById('hidden-input');
  if (hiddenInput) {
    console.log('[INIT] Setting up input handler');

    hiddenInput.addEventListener('keydown', handleFillInput);

    hiddenInput.addEventListener('blur', function() {
      if (gameState.isMyTurn) {
        setTimeout(function() { hiddenInput.focus(); }, 100);
      }
    });

    var fillContainer = document.querySelector('.fill-container');
    if (fillContainer) {
      fillContainer.addEventListener('click', function() {
        if (gameState.isMyTurn) {
          hiddenInput.focus();
        }
      });
    }
  }

  if (document.getElementById('history-list')) {
    loadHistory();
  }
});
