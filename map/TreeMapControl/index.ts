import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { TreeMap, ITreeMapProps, ITreeRecord } from "./TreeMap";
import * as React from "react";

export class TreeMapControl implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private context: ComponentFramework.Context<IInputs>;

    constructor() {
        // Empty
    }

    public init(
        context: ComponentFramework.Context<IInputs>,
        notifyOutputChanged: () => void,
        state: ComponentFramework.Dictionary
    ): void {
        this.context = context;
        context.parameters.sampleDataSet.paging.setPageSize(500);
    }

    // ポイントクリックで樹木情報画面に遷移する(機能要件#28)。
    // データセットが実際にバインドされているテーブルの論理名を
    // getTargetEntityType() で取得するため、発行元プレフィックス(new_等)を
    // コード側にハードコードする必要がない。
    private handleRecordClick = (id: string): void => {
        const entityName = this.context.parameters.sampleDataSet.getTargetEntityType();
        this.context.navigation
            .openForm({ entityName, entityId: id })
            .then(() => undefined)
            .catch((error: Error) => {
                console.error("[TreeMap] フォームを開けませんでした:", error);
            });
    };

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        this.context = context;

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

        // サブスクリプションキーの取得・保持はTreeMapコンポーネント自身のReact state
        // に任せる(webAPIだけを渡す)。PCFのnotifyOutputChanged/updateView再呼び出しに
        // 依存すると、コールド起動時の再描画取りこぼしが起こり得るため。
        const props: ITreeMapProps = {
            records,
            webAPI: context.webAPI,
            onRecordClick: this.handleRecordClick,
        };
        return React.createElement(TreeMap, props);
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // Add code to cleanup control if necessary
    }
}
