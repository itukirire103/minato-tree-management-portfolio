import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { TreeMap, ITreeMapProps, ITreeRecord } from "./TreeMap";
import * as React from "react";

// ComponentFramework.PropertyHelper.Types.PrivilegeType / PrivilegeDepth は
// 数値リテラル型で定義されているため、可読性のために名前を付けておく。
const PRIVILEGE_CREATE: ComponentFramework.PropertyHelper.Types.PrivilegeType = 1;
const PRIVILEGE_WRITE: ComponentFramework.PropertyHelper.Types.PrivilegeType = 3;
const PRIVILEGE_DEPTH_GLOBAL: ComponentFramework.PropertyHelper.Types.PrivilegeDepth = 3;

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

    // ドラッグで移動した先の緯度経度をDataverseへ保存する(機能要件#30/#31)。
    // latColumn/lngColumnはPCFのproperty-set名("latitude"/"longitude")ではなく、
    // ビュー側で実際にバインドされている列の論理名(例: new_latitude)を使う必要がある。
    private handlePositionChanged = (id: string, latitude: number, longitude: number): void => {
        const dataSet = this.context.parameters.sampleDataSet;
        const entityName = dataSet.getTargetEntityType();
        const latColumn = dataSet.columns.find((c) => c.alias === "latitude")?.name;
        const lngColumn = dataSet.columns.find((c) => c.alias === "longitude")?.name;
        if (!latColumn || !lngColumn) {
            console.error("[TreeMap] 緯度・経度列の論理名が取得できませんでした。");
            return;
        }
        this.context.webAPI
            .updateRecord(entityName, id, { [latColumn]: latitude, [lngColumn]: longitude })
            .then(() => {
                dataSet.refresh();
                return;
            })
            .catch((error: Error) => {
                console.error("[TreeMap] 位置情報の更新に失敗しました:", error);
            });
    };

    // 地図の空き地をクリックしたときに樹木を新規登録する(機能要件#29)。
    //
    // 当初は context.navigation.openForm() の parameters 引数(既定値の事前入力)で
    // 緯度・経度・ステータスをまとめて指定していたが、選択肢(OptionSet)型の
    // ステータスだけは既定値が反映されず、フォームの表示上の既定挙動により
    // 意図しない値(「伐採済」)で保存されてしまう不具合があった。
    // 数値・文字列は既定値の事前入力で問題なく機能するが、選択肢型は対応外と判断し、
    // ステータスを含むレコードを先に context.webAPI.createRecord() で確実に作成してから、
    // その作成済みレコードの編集フォームを開いて残りの項目(樹木番号・樹種等)を
    // 入力してもらう方式に変更した。
    private handleCreateNew = (latitude: number, longitude: number): void => {
        const dataSet = this.context.parameters.sampleDataSet;
        const entityName = dataSet.getTargetEntityType(); // 例: "new_tree"
        const latColumn = dataSet.columns.find((c) => c.alias === "latitude")?.name;
        const lngColumn = dataSet.columns.find((c) => c.alias === "longitude")?.name;
        const treeNumberColumn = dataSet.columns.find((c) => c.alias === "treeNumber")?.name;
        // "ステータス"はPCFのバインド列(property-set)に含まれないため、
        // データセットのエンティティ名から発行元プレフィックスを取り出して組み立てる
        // (entityNameは必ず "{prefix}_tree" という形式のため、末尾の"tree"を除いた
        //  部分がプレフィックスになる)。
        const prefix = entityName.slice(0, -"tree".length);
        const statusColumn = `${prefix}status`;

        const data: Record<string, unknown> = {};
        if (latColumn) data[latColumn] = latitude;
        if (lngColumn) data[lngColumn] = longitude;
        // create_tree_table.py の add_choice は選択肢の値を100000から順に
        // 割り当てるため、["現存", "伐採済", "植替え済"]の先頭「現存」は100000。
        data[statusColumn] = 100000;
        // 樹木番号(主要名列)はApplicationRequiredのため、作成時点で仮の値が必要。
        // ユーザーは直後に開く編集フォームで正式な番号に上書きできる。
        if (treeNumberColumn) data[treeNumberColumn] = `新規-${Date.now()}`;

        this.context.webAPI
            .createRecord(entityName, data)
            .then((result) => this.context.navigation.openForm({ entityName, entityId: result.id }))
            .then(() => {
                dataSet.refresh();
                return;
            })
            .catch((error: Error) => {
                console.error("[TreeMap] 新規登録に失敗しました:", error);
            });
    };

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        this.context = context;

        const dataSet = context.parameters.sampleDataSet;

        // init()でpaging.setPageSize(500)を設定しているが、初回の読み込みは
        // その設定が反映される前にプラットフォーム既定のページサイズ(500件より
        // 小さい)で走ってしまうことがあり、樹木が一部しか地図に表示されない
        // 不具合があった。hasNextPageが立っている間はloadNextPage()を呼び続け、
        // 全件読み込むまで自動的にページを送る(loadNextPage()は新しいデータが
        // 届くたびに次のupdateView()を発生させるため、この分岐が繰り返し評価され、
        // hasNextPageがfalseになった時点で自然に止まる)。
        if (!dataSet.loading && dataSet.paging.hasNextPage) {
            dataSet.paging.loadNextPage();
        }

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

        // 「管理者アカウント」を特定のロール名では判定せず、Dataverseの実際の
        // 権限(更新/作成)で判定する(機能要件#32)。ロール構成が変わっても
        // コード変更が不要で、セキュリティロール権限マトリクスの設計とも一致する。
        const entityName = dataSet.getTargetEntityType();
        const canEditPosition = context.utils.hasEntityPrivilege(entityName, PRIVILEGE_WRITE, PRIVILEGE_DEPTH_GLOBAL);
        const canCreate = context.utils.hasEntityPrivilege(entityName, PRIVILEGE_CREATE, PRIVILEGE_DEPTH_GLOBAL);

        // サブスクリプションキーの取得・保持はTreeMapコンポーネント自身のReact state
        // に任せる(webAPIだけを渡す)。PCFのnotifyOutputChanged/updateView再呼び出しに
        // 依存すると、コールド起動時の再描画取りこぼしが起こり得るため。
        const props: ITreeMapProps = {
            records,
            webAPI: context.webAPI,
            onRecordClick: this.handleRecordClick,
            canEditPosition,
            canCreate,
            onPositionChanged: this.handlePositionChanged,
            onCreateNew: this.handleCreateNew,
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
