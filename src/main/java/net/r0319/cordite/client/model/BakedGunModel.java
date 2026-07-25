package net.r0319.cordite.client.model;

import net.minecraft.resources.ResourceLocation;

import java.util.Map;

/**
 * ロード・ベイク済みの銃ジオメトリ1丁分。{@code root} は実体を持たない合成ルート
 * （geometry.json側で親を持たない複数のトップレベルボーンをまとめるためのラッパー）。
 */
public record BakedGunModel(GunBone root, Map<String, GunBone> byName, ResourceLocation texture) {}
