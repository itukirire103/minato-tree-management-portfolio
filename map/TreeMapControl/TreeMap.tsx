import * as React from "react";
import * as atlas from "azure-maps-control";
import "azure-maps-control/dist/atlas.min.css";

export interface ITreeMapProps {
    records: ITreeRecord[];
    subscriptionKey: string | null;
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

    // ---- 地図の初期化(サブスクリプションキーが取得できたら1回だけ) ----
    React.useEffect(() => {
        if (!props.subscriptionKey || !mapContainerRef.current || mapRef.current) return;

        const map = new atlas.Map(mapContainerRef.current, {
            authOptions: {
                // 環境変数から取得したサブスクリプションキーで認証する、最もシンプルな方式。
                // ブラウザでの追加のサインイン操作は一切発生しない。
                authType: atlas.AuthenticationType.subscriptionKey,
                subscriptionKey: props.subscriptionKey,
            },
            style: "road",
            center: [139.75, 35.66], // 港区芝周辺
            zoom: 14,
        });
        mapRef.current = map;

        return () => {
            map.dispose();
            mapRef.current = null;
        };
    }, [props.subscriptionKey]);

    // ---- 樹木データが変わるたびにピンを描画し直す ----
    React.useEffect(() => {
        const map = mapRef.current;
        if (!map) return;

        map.events.add("ready", () => {
            const dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);

            const points = props.records
                .filter((r) => r.latitude && r.longitude)
                .map((r) =>
                    new atlas.data.Feature(
                        new atlas.data.Point([r.longitude, r.latitude]),
                        { treeNumber: r.treeNumber, healthStatus: r.healthStatus }
                    )
                );
            dataSource.add(points);

            map.layers.add(
                new atlas.layer.SymbolLayer(dataSource, undefined, {
                    iconOptions: { image: "none" },
                    textOptions: {
                        textField: ["get", "treeNumber"],
                        offset: [0, 1.2],
                    },
                })
            );

            map.layers.add(
                new atlas.layer.BubbleLayer(dataSource, undefined, {
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
                })
            );
        });
    }, [props.records]);

    if (!props.subscriptionKey) {
        return <div style={{ padding: 16 }}>地図の設定を読み込んでいます...</div>;
    }

    return <div ref={mapContainerRef} style={{ width: "100%", height: "500px" }} />;
};
