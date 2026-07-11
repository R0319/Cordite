package net.r0319.cordite.registry;

import net.minecraft.world.item.Item;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.item.gun.GunProperties;

/**
 * アイテムのレジストリ。MVP では銃2種のみ。
 * 将来的には gunpack JSON からの動的登録に置き換える（docs/specs/01-gunpack.md）。
 */
public final class ModItems {
    private ModItems() {}

    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(Cordite.MODID);

    public static final DeferredItem<GunItem> GLOCK =
            ITEMS.register("glock", () -> new GunItem(GunProperties.GLOCK, new Item.Properties()));

    public static final DeferredItem<GunItem> AK47 =
            ITEMS.register("ak47", () -> new GunItem(GunProperties.AK47, new Item.Properties()));

    public static final DeferredItem<GunItem> M4A1 =
            ITEMS.register("m4a1", () -> new GunItem(GunProperties.M4A1, new Item.Properties()));
}
