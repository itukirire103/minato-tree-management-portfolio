import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { TreeMap, ITreeMapProps, ITreeRecord } from "./TreeMap";
import * as React from "react";

// create_env_variable.py で作成した環境変数のスキーマ名
const SUBSCRIPTION_KEY_SCHEMA_NAME = "new_AzureMapsSubscriptionKey";

// モジュールスコープのキャッシュ(クラスのインスタンスフィールドではない)。
// 初回のコールド起動時、データセットのロードと連動してコントロールのインスタンス自体が
// 複数回作り直されることがある。インスタンス単位でキーを持つと、作り直されるたびに
// 「非同期フェッチ→notifyOutputChanged→再描画」の競合が発生し、そのタイミング次第で
// 「地図の設定を読み込んでいます...」のまま止まる(要ハードリロード)。
// モジュールスコープに持たせることで、何度作り直されても2回目以降のインスタンスは
// updateView()の最初の呼び出しで同期的にキャッシュ済みの値を使えるため、この競合が起きない。
let cachedSubscriptionKey: string | null = null;
let fetchPromise: Promise<void> | null = null;

export class TreeMapControl implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private notifyOutputChanged: () => void;
    private context: ComponentFramework.Context<IInputs>;

    constructor() {
        // Empty
    }

    public init(
        context: ComponentFramework.Context<IInputs>,
        notifyOutputChanged: () => void,
        state: ComponentFramework.Dictionary
    ): void {
        this.notifyOutputChanged = notifyOutputChanged;
        this.context = context;
        context.parameters.sampleDataSet.paging.setPageSize(500);
        this.ensureSubscriptionKey();
    }

    // Dataverse環境変数からAzure Mapsのサブスクリプションキーを取得する。
    // 既に(このモジュール内のどのインスタインスでも)取得済み、または取得中であれば
    // 何もしない。取得できたら notifyOutputChanged() で再描画をトリガーする
    // (このコンポーネントはWeb API利用のためcontext.webAPIを使う。Dataverseに
    // 元々サインイン済みの状態を利用するため、追加のブラウザ認証は一切発生しない)。
    private ensureSubscriptionKey(): void {
        if (cachedSubscriptionKey !== null || fetchPromise !== null) return;
        console.log("[TreeMap] 環境変数の取得を開始します。");

        const options =
            "?$select=value&$expand=EnvironmentVariableDefinitionId" +
            `&$filter=(EnvironmentVariableDefinitionId/schemaname eq '${SUBSCRIPTION_KEY_SCHEMA_NAME}')`;

        fetchPromise = this.context.webAPI
            .retrieveMultipleRecords("environmentvariablevalue", options)
            .then((result) => {
                console.log("[TreeMap] 環境変数の取得結果:", result);
                if (result.entities.length > 0) {
                    cachedSubscriptionKey = result.entities[0].value as string;
                    console.log("[TreeMap] キーを取得しました(先頭5文字):", cachedSubscriptionKey.substring(0, 5));
                } else {
                    console.error(`[TreeMap] 環境変数『${SUBSCRIPTION_KEY_SCHEMA_NAME}』の値が見つかりません。`);
                }
                this.notifyOutputChanged();
                console.log("[TreeMap] notifyOutputChangedを呼び出しました。");
                return;
            })
            .catch((error: Error) => {
                console.error("[TreeMap] 環境変数の取得に失敗しました:", error);
                fetchPromise = null; // リトライできるようにする
            });
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        this.context = context;
        this.ensureSubscriptionKey();

        const dataSet = context.parameters.sampleDataSet;
        const records: ITreeRecord[] = dataSet.sortedRecordIds.map((id: string) => {
            const record = dataSet.records[id];
            return {
                id,
                treeNumber: String(record.getFormattedValue("treeNumber") ?? ""),
                latitude: Number(record.getValue("latitude") ?? 0),
                longitude: Number(record.getValue("longitude") ?? 0),
                healthStatus: record.getFormattedValue("healthStatus") || undefined,
            };
        });

        const props: ITreeMapProps = { records, subscriptionKey: cachedSubscriptionKey };
        return React.createElement(TreeMap, props);
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // Add code to cleanup control if necessary
    }
}
