const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const messageEl = document.getElementById("goalMessage");

const gravity = 0.5;
const KEY_LEFT = "a";
const KEY_RIGHT = "d";
const KEY_JUMP = " ";
const controlKeys = new Set([KEY_LEFT, KEY_RIGHT, KEY_JUMP]);
const keys = {
  [KEY_LEFT]: false,
  [KEY_RIGHT]: false,
  [KEY_JUMP]: false
};

// ステージ全体の幅
const STAGE_WIDTH = 3000;
const START_POSITION = Object.freeze({ x: 50, y: 300 });

// 足場（横長の地面 + 数個のブロック）
const platforms = [
  { x: 0, y: 350, w: STAGE_WIDTH, h: 50 }, // ground
  { x: 400, y: 300, w: 120, h: 20 },
  { x: 800, y: 250, w: 100, h: 20 },
  { x: 1200, y: 280, w: 100, h: 20 },
  { x: 1600, y: 260, w: 100, h: 20 },
  { x: 2000, y: 240, w: 120, h: 20 }
];

// ゴール
const goal = { x: 2800, y: 300, w: 40, h: 60 };

const goalState = { active: false, triggeredAt: 0 };
const GOAL_MESSAGE_DURATION = 2000;

const player = {
  x: START_POSITION.x,
  y: START_POSITION.y,
  width: 30,
  height: 30,
  dx: 0,
  dy: 0,
  speed: 4,
  jumpForce: 12,
  grounded: false,
  draw() {
    ctx.save();
    ctx.font = "30px 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif";
    ctx.textBaseline = "top";
    ctx.fillText("♡", this.x, this.y);
    ctx.restore();
  },
  update(platformList) {
    const prevX = this.x;
    this.x += this.dx;
    this.x = clamp(this.x, 0, STAGE_WIDTH - this.width);

    // 横方向の衝突
    platformList.forEach(p => {
      if (isIntersecting(this, p)) {
        if (this.dx > 0 && prevX + this.width <= p.x) {
          this.x = p.x - this.width;
          this.dx = 0;
        } else if (this.dx < 0 && prevX >= p.x + p.w) {
          this.x = p.x + p.w;
          this.dx = 0;
        }
      }
    });
    this.x = clamp(this.x, 0, STAGE_WIDTH - this.width);

    const prevY = this.y;
    this.dy += gravity;
    this.y += this.dy;

    this.grounded = false;
    platformList.forEach(p => {
      if (isIntersecting(this, p)) {
        if (this.dy > 0 && prevY + this.height <= p.y) {
          this.y = p.y - this.height;
          this.dy = 0;
          this.grounded = true;
        } else if (this.dy < 0 && prevY >= p.y + p.h) {
          this.y = p.y + p.h;
          this.dy = 0;
        }
      }
    });

    if (this.y > canvas.height) {
      resetGame();
    }
  }
};

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

// 衝突判定
function isIntersecting(a, b) {
  return (
    a.x < b.x + b.w &&
    a.x + a.width > b.x &&
    a.y < b.y + b.h &&
    a.y + a.height > b.y
  );
}

function handleInput() {
  let move = 0;
  if (keys[KEY_LEFT]) move -= 1;
  if (keys[KEY_RIGHT]) move += 1;
  player.dx = move * player.speed;

  if (keys[KEY_JUMP] && player.grounded) {
    player.dy = -player.jumpForce;
    player.grounded = false;
  }
}

document.addEventListener("keydown", e => {
  const key = e.key.toLowerCase();
  if (controlKeys.has(key)) {
    e.preventDefault();
    keys[key] = true;
  }
});
document.addEventListener("keyup", e => {
  const key = e.key.toLowerCase();
  if (controlKeys.has(key)) {
    e.preventDefault();
    keys[key] = false;
  }
});

function showGoalMessage() {
  messageEl.textContent = "ゴール！2秒後に再スタート（クリックでもOK）";
  messageEl.classList.remove("hidden");
}

function hideGoalMessage() {
  messageEl.classList.add("hidden");
  messageEl.textContent = "";
}

function triggerGoal(timestamp) {
  goalState.active = true;
  goalState.triggeredAt = timestamp;
  showGoalMessage();
}

messageEl.addEventListener("click", () => {
  if (goalState.active) resetGame();
});

function resetGame() {
  hideGoalMessage();
  goalState.active = false;
  goalState.triggeredAt = 0;
  player.x = START_POSITION.x;
  player.y = START_POSITION.y;
  player.dx = 0;
  player.dy = 0;
  player.grounded = false;
  Object.keys(keys).forEach(k => (keys[k] = false));
}

// カメラ
let cameraX = 0;

function drawPlatforms() {
  ctx.fillStyle = "#654321";
  platforms.forEach(p => ctx.fillRect(p.x, p.y, p.w, p.h));
}

function drawGoal() {
  ctx.fillStyle = goalState.active ? "#ffe066" : "#ffd700";
  ctx.fillRect(goal.x, goal.y, goal.w, goal.h);
}

function update(timestamp = 0) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!goalState.active) {
    handleInput();
    player.update(platforms);

    if (isIntersecting(player, goal)) {
      triggerGoal(timestamp);
    }
  } else {
    player.dx = 0;
    player.dy = 0;
  }

  const targetCameraX = player.x - canvas.width / 2;
  const maxCameraX = Math.max(0, STAGE_WIDTH - canvas.width);
  cameraX = clamp(targetCameraX, 0, maxCameraX);

  ctx.save();
  ctx.translate(-cameraX, 0);

  drawPlatforms();
  drawGoal();
  player.draw();

  ctx.restore();

  if (goalState.active && timestamp - goalState.triggeredAt >= GOAL_MESSAGE_DURATION) {
    resetGame();
  }

  requestAnimationFrame(update);
}

resetGame();
requestAnimationFrame(update);
