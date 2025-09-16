const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const messageEl = document.getElementById("goalMessage");

const gravity = 0.5;
const controlKeys = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]);
const keys = {};

const platforms = [
  { x: 0, y: 350, w: 800, h: 50 }, // ground
  { x: 150, y: 300, w: 100, h: 20 },
  { x: 300, y: 250, w: 100, h: 20 },
  { x: 500, y: 280, w: 100, h: 20 }
];

const goal = { x: 730, y: 300, w: 30, h: 50 };

const goalState = {
  active: false,
  triggeredAt: 0
};
const GOAL_MESSAGE_DURATION = 2000;

const player = {
  x: 50,
  y: 300,
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
    const horizontalVelocity = this.dx;
    const previousX = this.x;
    this.x += horizontalVelocity;

    platformList.forEach(platform => {
      if (isIntersecting(this, platform)) {
        if (horizontalVelocity > 0 && previousX + this.width <= platform.x) {
          this.x = platform.x - this.width;
          this.dx = 0;
        } else if (horizontalVelocity < 0 && previousX >= platform.x + platform.w) {
          this.x = platform.x + platform.w;
          this.dx = 0;
        }
      }
    });

    const previousY = this.y;
    this.dy += gravity;
    const verticalVelocity = this.dy;
    this.y += verticalVelocity;

    this.grounded = false;
    platformList.forEach(platform => {
      if (isIntersecting(this, platform)) {
        if (verticalVelocity > 0 && previousY + this.height <= platform.y) {
          this.y = platform.y - this.height;
          this.dy = 0;
          this.grounded = true;
        } else if (verticalVelocity < 0 && previousY >= platform.y + platform.h) {
          this.y = platform.y + platform.h;
          this.dy = 0;
        }
      }
    });

    if (this.x < 0) this.x = 0;
    if (this.x + this.width > canvas.width) this.x = canvas.width - this.width;
    if (this.y < 0) {
      this.y = 0;
      this.dy = 0;
    }
    if (this.y > canvas.height) {
      resetGame();
    }
  }
};

function isIntersecting(a, b) {
  return (
    a.x < b.x + b.w &&
    a.x + a.width > b.x &&
    a.y < b.y + b.h &&
    a.y + a.height > b.y
  );
}

function handleInput() {
  player.dx = 0;
  if (keys.ArrowLeft) player.dx = -player.speed;
  if (keys.ArrowRight) player.dx = player.speed;
  if (keys.ArrowUp && player.grounded) {
    player.dy = -player.jumpForce;
    player.grounded = false;
  }
}

function onKeyDown(event) {
  if (controlKeys.has(event.key)) {
    event.preventDefault();
    keys[event.key] = true;
  }
}

function onKeyUp(event) {
  if (controlKeys.has(event.key)) {
    event.preventDefault();
    keys[event.key] = false;
  }
}

document.addEventListener("keydown", onKeyDown, { passive: false });
document.addEventListener("keyup", onKeyUp, { passive: false });

function showGoalMessage() {
  messageEl.textContent = "ゴール！ クリックするとすぐに再スタートします。";
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
  if (goalState.active) {
    resetGame();
  }
});

function resetGame() {
  hideGoalMessage();
  goalState.active = false;
  goalState.triggeredAt = 0;
  player.x = 50;
  player.y = 300;
  player.dx = 0;
  player.dy = 0;
  player.grounded = false;
  Object.keys(keys).forEach(key => {
    keys[key] = false;
  });
}

function drawPlatforms() {
  ctx.fillStyle = "#654321";
  platforms.forEach(platform => {
    ctx.fillRect(platform.x, platform.y, platform.w, platform.h);
  });
}

function drawGoal() {
  ctx.fillStyle = goalState.active ? "#ffe066" : "#ffd700";
  ctx.fillRect(goal.x, goal.y, goal.w, goal.h);
}

function update(timestamp = 0) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!goalState.active) {
    handleInput();
  } else {
    player.dx = 0;
  }

  player.update(platforms);
  drawPlatforms();
  drawGoal();
  player.draw();

  if (!goalState.active && isIntersecting(player, goal)) {
    triggerGoal(timestamp);
  }

  if (goalState.active && timestamp - goalState.triggeredAt >= GOAL_MESSAGE_DURATION) {
    resetGame();
  }

  requestAnimationFrame(update);
}

resetGame();
requestAnimationFrame(update);
