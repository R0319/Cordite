package net.r0319.cordite.client.model;

import org.joml.Vector3f;

import java.util.List;

/**
 * ジオメトリのボーン1個。{@code localOffset} は親ボーンpivotからの相対オフセット
 * （Java座標系・1/16スケール適用済み）で、レンダラーはこれを毎フレーム {@code translate} するだけでよい。
 */
public final class GunBone {
    public final String name;
    public final Vector3f localOffset;
    public final List<BakedCube> cubes;
    public final List<GunBone> children;

    public GunBone(String name, Vector3f localOffset, List<BakedCube> cubes, List<GunBone> children) {
        this.name = name;
        this.localOffset = localOffset;
        this.cubes = cubes;
        this.children = children;
    }
}
