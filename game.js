 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/game.js
index 0000000000000000000000000000000000000000..d7c2e3e43b244bbee145a9f8e7d23ffaa391545e 100644
--- a//dev/null
+++ b/game.js
@@ -0,0 +1,117 @@
+// --- basic setup ---
+const canvas = document.getElementById("game");
+const ctx = canvas.getContext("2d");
+const gravity = 0.5;
+
+const player = {
+  x: 50,
+  y: 300,
+  width: 30,
+  height: 30,
+  dx: 0,
+  dy: 0,
+  speed: 4,
+  jumpForce: 12,
+  grounded: false,
+  draw() {
+    ctx.font = "30px Arial";
+    ctx.fillText("♡", this.x, this.y + this.height);
+  },
+  update() {
+    // horizontal movement
+    this.x += this.dx;
+
+    // gravity
+    this.dy += gravity;
+    this.y += this.dy;
+
+    // simple ground collision
+    this.grounded = false;
+    platforms.forEach(p => {
+      if (
+        this.x < p.x + p.w &&
+        this.x + this.width > p.x &&
+        this.y < p.y + p.h &&
+        this.y + this.height > p.y
+      ) {
+        // landed on top
+        if (this.dy > 0 && this.y + this.height <= p.y + this.dy) {
+          this.y = p.y - this.height;
+          this.dy = 0;
+          this.grounded = true;
+        }
+      }
+    });
+
+    // boundary checks
+    if (this.x < 0) this.x = 0;
+    if (this.x + this.width > canvas.width)
+      this.x = canvas.width - this.width;
+    if (this.y > canvas.height) resetGame();
+  }
+};
+
+// --- platforms & goal ---
+const platforms = [
+  { x: 0, y: 350, w: 800, h: 50 },          // ground
+  { x: 150, y: 300, w: 100, h: 20 },
+  { x: 300, y: 250, w: 100, h: 20 },
+  { x: 500, y: 280, w: 100, h: 20 }
+];
+
+const goal = { x: 730, y: 300, w: 30, h: 50 };
+
+// --- input handling ---
+const keys = {};
+document.addEventListener("keydown", e => (keys[e.key] = true));
+document.addEventListener("keyup", e => (keys[e.key] = false));
+
+function handleInput() {
+  player.dx = 0;
+  if (keys["ArrowLeft"]) player.dx = -player.speed;
+  if (keys["ArrowRight"]) player.dx = player.speed;
+  if (keys["ArrowUp"] && player.grounded) {
+    player.dy = -player.jumpForce;
+    player.grounded = false;
+  }
+}
+
+// --- core loop ---
+function update() {
+  ctx.clearRect(0, 0, canvas.width, canvas.height);
+
+  handleInput();
+  player.update();
+  player.draw();
+
+  // draw platforms
+  ctx.fillStyle = "#654321";
+  platforms.forEach(p => ctx.fillRect(p.x, p.y, p.w, p.h));
+
+  // draw goal
+  ctx.fillStyle = "yellow";
+  ctx.fillRect(goal.x, goal.y, goal.w, goal.h);
+
+  // goal check
+  if (
+    player.x < goal.x + goal.w &&
+    player.x + player.width > goal.x &&
+    player.y < goal.y + goal.h &&
+    player.y + player.height > goal.y
+  ) {
+    alert("ゴール！");
+    resetGame();
+  }
+
+  requestAnimationFrame(update);
+}
+
+// --- reset and start ---
+function resetGame() {
+  player.x = 50;
+  player.y = 300;
+  player.dx = 0;
+  player.dy = 0;
+}
+
+update();
 
EOF
)
