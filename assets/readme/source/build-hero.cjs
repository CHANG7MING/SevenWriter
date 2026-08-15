const fs = require("fs");

const layoutPath = "assets/readme/source/hero-layout.svg";
const subjectPath = "assets/readme/source/hero-subject.png";
const outputPath = "assets/readme/hero.svg";
const placeholder = 'href="hero-subject.png"';
const layout = fs.readFileSync(layoutPath, "utf8");
const base64 = fs.readFileSync(subjectPath).toString("base64");
if (!layout.includes(placeholder)) throw new Error("image placeholder not found");
fs.writeFileSync(outputPath, layout.replace(placeholder, `href="data:image/png;base64,${base64}"`), "utf8");
