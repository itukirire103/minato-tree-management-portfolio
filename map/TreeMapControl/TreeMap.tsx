import * as React from "react";
import * as atlas from "azure-maps-control";
import "azure-maps-control/dist/atlas.min.css";

// create_env_variable.py で作成した環境変数のスキーマ名
const SUBSCRIPTION_KEY_SCHEMA_NAME = "new_AzureMapsSubscriptionKey";

export interface ITreeMapProps {
    records: ITreeRecord[];
    webAPI: ComponentFramework.WebApi;
    onRecordClick?: (id: string) => void;
    canEditPosition?: boolean;
    canCreate?: boolean;
    onPositionChanged?: (id: string, latitude: number, longitude: number) => void;
    onCreateNew?: (latitude: number, longitude: number) => void;
}

export interface ITreeRecord {
    id: string;
    treeNumber: string;
    latitude: number;
    longitude: number;
    healthStatus?: string;
}

// 健全度に応じたピンの色分け(A=緑, B1=黄, B2=橙, C=赤, 不明=灰)
function colorForHealth(status?: string): string {
    switch (status) {
        case "A": return "#2E7D32";
        case "B1": return "#F9A825";
        case "B2": return "#EF6C00";
        case "C": return "#C62828";
        default: return "#757575";
    }
}

export const TreeMap: React.FC<ITreeMapProps> = (props) => {
    const mapContainerRef = React.useRef<HTMLDivElement>(null);
    const mapRef = React.useRef<atlas.Map | null>(null);
    const dataSourceRef = React.useRef<atlas.source.DataSource | null>(null);
    const recordsRef = React.useRef(props.records);
    const onRecordClickRef = React.useRef(props.onRecordClick);
    const canEditPositionRef = React.useRef(props.canEditPosition);
    const canCreateRef = React.useRef(props.canCreate);
    const onPositionChangedRef = React.useRef(props.onPositionChanged);
    const onCreateNewRef = React.useRef(props.onCreateNew);
    recordsRef.current = props.records;
    onRecordClickRef.current = props.onRecordClick;
    canEditPositionRef.current = props.canEditPosition;
    canCreateRef.current = props.canCreate;
    onPositionChangedRef.current = props.onPositionChanged;
    onCreateNewRef.current = props.onCreateNew;

    // Azure Mapsのサブスクリプションキー。PCF側(notifyOutputChanged経由)の
    // 再描画シグナルには頼らず、Reactコンポーネント自身のstateとして管理する。
    // PCFプラットフォームがコントロールを作り直した場合でも、そのとき生きている
    // (マウントされている)TreeMapインスタンス自身がフェッチしてsetStateするため、
    // 「取得はできたが画面に反映されない」という競合がそもそも起こり得ない。
    const [subscriptionKey, setSubscriptionKey] = React.useState<string | null>(null);
    const webAPIRef = React.useRef(props.webAPI);
    webAPIRef.current = props.webAPI;

    // ---- サブスクリプションキーの取得(マウント時に1回だけ) ----
    React.useEffect(() => {
        let cancelled = false;
        console.log("[TreeMap] 環境変数の取得を開始します。");

        const options =
            "?$select=value&$expand=EnvironmentVariableDefinitionId" +
            `&$filter=(EnvironmentVariableDefinitionId/schemaname eq '${SUBSCRIPTION_KEY_SCHEMA_NAME}')`;

        webAPIRef.current
            .retrieveMultipleRecords("environmentvariablevalue", options)
            .then((result) => {
                console.log("[TreeMap] 環境変数の取得結果:", result);
                if (cancelled) return;
                if (result.entities.length > 0) {
                    const key = result.entities[0].value as string;
                    console.log("[TreeMap] キーを取得しました(先頭5文字):", key.substring(0, 5));
                    setSubscriptionKey(key);
                } else {
                    console.error(`[TreeMap] 環境変数『${SUBSCRIPTION_KEY_SCHEMA_NAME}』の値が見つかりません。`);
                }
                return;
            })
            .catch((error: Error) => {
                console.error("[TreeMap] 環境変数の取得に失敗しました:", error);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    // データソースの中身を樹木レコードで置き換える(レイヤー自体は作り直さない)。
    const syncPoints = React.useCallback((records: ITreeRecord[]) => {
        const dataSource = dataSourceRef.current;
        if (!dataSource) return;
        const points = records
            .filter((r) => r.latitude && r.longitude)
            .map((r) =>
                new atlas.data.Feature(
                    new atlas.data.Point([r.longitude, r.latitude]),
                    { id: r.id, treeNumber: r.treeNumber, healthStatus: r.healthStatus }
                )
            );
        dataSource.clear();
        dataSource.add(points);
    }, []);

    // ---- 地図の初期化(サブスクリプションキーが取得できたら1回だけ) ----
    React.useEffect(() => {
        if (!subscriptionKey || !mapContainerRef.current || mapRef.current) return;

        const map = new atlas.Map(mapContainerRef.current, {
            authOptions: {
                // 環境変数から取得したサブスクリプションキーで認証する、最もシンプルな方式。
                // ブラウザでの追加のサインイン操作は一切発生しない。
                authType: atlas.AuthenticationType.subscriptionKey,
                subscriptionKey: subscriptionKey,
            },
            style: "road",
            center: [139.75, 35.66], // 港区芝周辺
            zoom: 14,
        });
        mapRef.current = map;

        // レイヤー・イベントハンドラの登録は"ready"内で1回だけ行う。
        map.events.add("ready", () => {
            const dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);
            dataSourceRef.current = dataSource;
            syncPoints(recordsRef.current);

            const symbolLayer = new atlas.layer.SymbolLayer(dataSource, undefined, {
                iconOptions: { image: "none" },
                textOptions: {
                    textField: ["get", "treeNumber"],
                    offset: [0, 1.2],
                },
            });
            map.layers.add(symbolLayer);

            const bubbleLayer = new atlas.layer.BubbleLayer(dataSource, undefined, {
                radius: 6,
                color: [
                    "match",
                    ["get", "healthStatus"],
                    "A", colorForHealth("A"),
                    "B1", colorForHealth("B1"),
                    "B2", colorForHealth("B2"),
                    "C", colorForHealth("C"),
                    colorForHealth(undefined),
                ],
            });
            map.layers.add(bubbleLayer);

            // ---- ドラッグでの位置修正(機能要件#30/#31、更新権限がある場合のみ) ----
            // Azure Mapsのデータ駆動レイヤーはネイティブのドラッグ操作を持たないため、
            // mousedown→mousemove→mouseupを自前で追跡する定番の実装パターンを使う。
            let draggedShape: atlas.Shape | null = null;
            let didDrag = false;

            map.events.add("mousedown", bubbleLayer, (e) => {
                if (!canEditPositionRef.current) return;
                const shape = e.shapes?.[0];
                if (!(shape instanceof atlas.Shape)) return;
                draggedShape = shape;
                didDrag = false;
                // dragPanInteractionはここで無効化するのではなく、下のmouseenterで
                // ポイントにマウスが乗った時点で先に無効化しておく。mousedown後に
                // 無効化すると、地図自体のパン操作(ドラッグ)と競合し、ポイントではなく
                // 地図全体が動いてしまうことがあるため。
                map.getCanvasContainer().style.cursor = "grabbing";
            });

            map.events.add("mousemove", (e) => {
                if (!draggedShape || !e.position) return;
                didDrag = true;
                draggedShape.setCoordinates(e.position);
            });

            map.events.add("mouseup", () => {
                if (!draggedShape) return;
                // ドロップ位置がbubbleLayerの外(=マウスを乗せたままのmouseleaveが
                // 発生しない場所)である可能性があるため、ここでも明示的に復元する。
                map.setUserInteraction({ dragPanInteraction: true });
                map.getCanvasContainer().style.cursor = "grab";
                if (didDrag) {
                    const id = (draggedShape.getProperties() as { id?: string }).id;
                    const coords = draggedShape.getCoordinates() as atlas.data.Position;
                    if (id) onPositionChangedRef.current?.(id, coords[1], coords[0]);
                }
                draggedShape = null;
            });

            // ---- クリック: ポイントなら詳細画面へ遷移(#28)、
            //      空き地なら新規登録(#29、作成権限がある場合のみ) ----
            map.events.add("click", (e: atlas.MapMouseEvent) => {
                if (didDrag) {
                    // ドラッグ操作の直後に発生するクリックは無視する。
                    didDrag = false;
                    return;
                }
                const shape = e.shapes?.[0];
                if (shape instanceof atlas.Shape) {
                    const id = (shape.getProperties() as { id?: string }).id;
                    if (id) onRecordClickRef.current?.(id);
                    return;
                }
                if (canCreateRef.current && e.position) {
                    onCreateNewRef.current?.(e.position[1], e.position[0]);
                }
            });

            // ポイントにマウスが乗った時点で、地図自体のパン操作を先に無効化しておく。
            // (mousedown時点で無効化すると、地図のパンとポイントのドラッグが競合し、
            //  ポイントではなく地図全体が動いてしまうことがあるため)
            map.events.add("mouseenter", bubbleLayer, () => {
                if (canEditPositionRef.current) {
                    map.setUserInteraction({ dragPanInteraction: false });
                }
                map.getCanvasContainer().style.cursor = canEditPositionRef.current ? "grab" : "pointer";
            });
            map.events.add("mouseleave", bubbleLayer, () => {
                if (!draggedShape) {
                    map.setUserInteraction({ dragPanInteraction: true });
                }
                map.getCanvasContainer().style.cursor = "default";
            });
        });

        return () => {
            map.dispose();
            mapRef.current = null;
            dataSourceRef.current = null;
        };
    }, [subscriptionKey, syncPoints]);

    // ---- 樹木データが変わるたびにピンを描画し直す ----
    React.useEffect(() => {
        syncPoints(props.records);
    }, [props.records, syncPoints]);

    if (!subscriptionKey) {
        return <div style={{ padding: 16 }}>地図の設定を読み込んでいます...</div>;
    }

    return <div ref={mapContainerRef} style={{ width: "100%", height: "500px" }} />;
};
