import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { TreeMap, ITreeMapProps, ITreeRecord } from "./TreeMap";
import * as React from "react";

// setup_azure_maps_aad.ps1 / create_env_variable.py で作成した環境変数のスキーマ名
const SUBSCRIPTION_KEY_SCHEMA_NAME = "new_AzureMapsSubscriptionKey";

export class TreeMapControl implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private notifyOutputChanged: () => void;
    private context: ComponentFramework.Context<IInputs>;
    private subscriptionKey: string | null = null;
    private keyFetchStarted = false;

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
    }

    // Dataverse環境変数からAzure Mapsのサブスクリプションキーを取得する。
    // 取得できたら notifyOutputChanged() で再描画をトリガーする(このコンポーネントは
    // Web API利用のためcontext.webAPIを使う。Dataverseに元々サインイン済みの状態を
    // 利用するため、追加のブラウザ認証は一切発生しない)。
    private fetchSubscriptionKey(): void {
        if (this.keyFetchStarted) return;
        this.keyFetchStarted = true;
        console.log("[TreeMap] 環境変数の取得を開始します。");

        const options =
            "?$select=value&$expand=EnvironmentVariableDefinitionId" +
            `&$filter=(EnvironmentVariableDefinitionId/schemaname eq '${SUBSCRIPTION_KEY_SCHEMA_NAME}')`;

        this.context.webAPI
            .retrieveMultipleRecords("environmentvariablevalue", options)
            .then((result) => {
                console.log("[TreeMap] 環境変数の取得結果:", result);
                if (result.entities.length > 0) {
                    this.subscriptionKey = result.entities[0].value as string;
                    console.log("[TreeMap] キーを取得しました(先頭5文字):", this.subscriptionKey.substring(0, 5));
                } else {
                    console.error(`[TreeMap] 環境変数『${SUBSCRIPTION_KEY_SCHEMA_NAME}』の値が見つかりません。`);
                }
                this.notifyOutputChanged();
                console.log("[TreeMap] notifyOutputChangedを呼び出しました。");
                return;
            })
            .catch((error: Error) => {
                console.error("[TreeMap] 環境変数の取得に失敗しました:", error);
                this.notifyOutputChanged();
            });
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        this.context = context;
        this.fetchSubscriptionKey();

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

        const props: ITreeMapProps = { records, subscriptionKey: this.subscriptionKey };
        return React.createElement(TreeMap, props);
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // Add code to cleanup control if necessary
    }
}
