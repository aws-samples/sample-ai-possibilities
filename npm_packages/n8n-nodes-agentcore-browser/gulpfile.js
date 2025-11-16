const gulp = require('gulp');

function buildIcons() {
  const nodeTypes = ['AgentcoreBrowser'];

  return gulp.src(`nodes/**/*.{png,svg}`)
    .pipe(gulp.dest('dist/nodes'));
}

exports['build:icons'] = buildIcons;
exports.default = buildIcons;
