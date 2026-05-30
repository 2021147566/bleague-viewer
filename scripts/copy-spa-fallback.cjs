const fs = require("fs");
const path = require("path");

const index = path.join("dist", "index.html");
const fallback = path.join("dist", "404.html");
fs.copyFileSync(index, fallback);
console.log("Copied dist/index.html -> dist/404.html (GitHub Pages SPA)");
