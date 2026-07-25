package net.r0319.cordite.client.model;

import org.joml.Vector3f;

import java.util.List;

/**
 * ジオメトリのボーン1個。{@code localOffset} は親ボーンpivotからの相対オフセット
 * （Java座標系・1/16スケール適用済み）で、レンダラーはこれを毎フレーム {@code translate} するだけでよい。
 */
public final class GunBone {
    public final String name;
    /** 親ボーンpivotからの相対オフセット（Java座標系・ブロック単位）。 */
    public final Vector3f localOffset;
    /**
     * モデル原点からこのボーンpivotまでの累積オフセット（rest状態・Java座標系・ブロック単位）。
     * 階層をたどらずにロケーターの位置を得るために持つ。
     */
    public final Vector3f modelOffset;
    public final List<BakedCube> cubes;
    public final List<GunBone> children;
    /**
     * 全キューブ（per-face UVでないため描画対象から外したものも含む）のボーンローカルAABB。
     * キューブを1つも持たないボーン（ロケーター等）では null。
     * ハンドアンカー（{@code right_hand}/{@code left_hand} のプレースホルダ箱にバニラの腕を重ねる）
     * の基準に使うため、描画可否とは独立に保持する。
     */
    public final Vector3f boundsMin;
    public final Vector3f boundsMax;
    /**
     * 親ボーン（トップレベルなら null）。任意のボーンまでの変換を根元からたどるために持つ。
     * 子を先にベイクしてから親を生成する都合上、生成後に {@link #linkChildren()} で設定する。
     */
    public GunBone parent;

    public GunBone(String name, Vector3f localOffset, Vector3f modelOffset, List<BakedCube> cubes,
                   List<GunBone> children, Vector3f boundsMin, Vector3f boundsMax) {
        this.name = name;
        this.localOffset = localOffset;
        this.modelOffset = modelOffset;
        this.cubes = cubes;
        this.children = children;
        this.boundsMin = boundsMin;
        this.boundsMax = boundsMax;
    }

    /** 直下の子に自分を親として設定する。 */
    public void linkChildren() {
        for (GunBone child : children) {
            child.parent = this;
        }
    }
}
