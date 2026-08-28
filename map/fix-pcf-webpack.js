/**
 * fix-pcf-webpack.js
 * ---------------------
 * (仮称)樹木管理システム ポートフォリオ用
 *
 * pcf-scripts の webpackConfig.js は、node_modules配下の.jsファイルも
 * 無条件にBabelでトランスパイルしてしまう。これにより azure-maps-control の
 * 既製バンドル(atlas-esm.min.js)内のWeb Worker用コードが壊れ、
 * "_toArray is not defined" のような実行時エラーで地図タイルが描画されない
 * 不具合が起きる(2026年時点でMicrosoft公式の修正は未提供)。
 *
 * npm install のたびに node_modules が再生成され、このパッチも消えるため、
 * package.json の postinstall フックからこのスクリプトを実行して自動再適用する。
 */

const fs = require("fs");
const path = require("path");

const TARGET = path.join(__dirname, "node_modules", "pcf-scripts", "webpackConfig.js");

const ORIGINAL_SNIPPET =
`                {
                    // Tell webpack how to handle JS, JSX, MJS, or MJSX files
                    test: /\\.(jsx?|mjsx?)$/,
                    use: [babelLoader],
                },`;

const PATCHED_SNIPPET =
`                {
                    // Tell webpack how to handle JS, JSX, MJS, or MJSX files
                    test: /\\.(jsx?|mjsx?)$/,
                    use: [babelLoader],
                    // node_modules配下(azure-maps-control等の既製バンドル)をBabelで
                    // 再トランスパイルすると、Web Worker内で使うヘルパー関数が抜け落ち
                    // "_toArray is not defined" のようなランタイムエラーになるため除外する。
                    exclude: /node_modules/,
                },`;

function main() {
    if (!fs.existsSync(TARGET)) {
        console.log("[fix-pcf-webpack] pcf-scripts/webpackConfig.js が見つかりません。スキップします。");
        return;
    }

    const content = fs.readFileSync(TARGET, "utf8");

    if (content.includes("exclude: /node_modules/,")) {
        console.log("[fix-pcf-webpack] 既にパッチ適用済みです。何もしません。");
        return;
    }

    if (!content.includes(ORIGINAL_SNIPPET)) {
        console.warn(
            "[fix-pcf-webpack] [警告] 想定したコード片が見つかりませんでした。" +
            "pcf-scriptsのバージョンが変わった可能性があります。手動で確認してください。"
        );
        return;
    }

    fs.writeFileSync(TARGET, content.replace(ORIGINAL_SNIPPET, PATCHED_SNIPPET), "utf8");
    console.log("[fix-pcf-webpack] pcf-scripts/webpackConfig.js にパッチを適用しました(node_modulesをBabelから除外)。");
}

main();
