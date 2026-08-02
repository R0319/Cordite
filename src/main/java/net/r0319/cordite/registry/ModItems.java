package net.r0319.cordite.registry;

import net.minecraft.world.item.Item;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.GunItem;

/**
 * アイテムのレジストリ。銃種は gun_id コンポーネントと gunpack 定義で区別する。
 */
public final class ModItems {
    private ModItems() {}

    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(Cordite.MODID);

    public static final DeferredItem<GunItem> GUN =
            ITEMS.register("gun", () -> new GunItem(new Item.Properties()));
}
