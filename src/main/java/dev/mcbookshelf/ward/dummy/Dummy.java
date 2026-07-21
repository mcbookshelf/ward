package dev.mcbookshelf.ward.dummy;

import java.util.Objects;
import java.util.Set;
import java.util.UUID;

import com.mojang.authlib.GameProfile;

import net.minecraft.advancements.triggers.CriteriaTriggers;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.DisconnectionDetails;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundEntityPositionSyncPacket;
import net.minecraft.network.protocol.game.ClientboundRotateHeadPacket;
import net.minecraft.network.protocol.game.ServerboundClientCommandPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.TickTask;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

/**
 * A fake server-side player with a no-op network connection. Dummies are never saved and keep
 * their stats and advancements in memory. Inspired by <a href="https://github.com/gnembon/fabric-carpet">Carpet</a>.
 */
public class Dummy extends ServerPlayer {
	public final Vec3 ward$originalSpawnPosition;
	public final Vec2 ward$originalSpawnRotation;

	/**
	 * Creates and spawns a dummy with a randomly generated name.
	 */
	public static Dummy create(ServerLevel level, Vec3 position, Vec2 rotation) {
		PlayerList players = level.getServer().getPlayerList();
		String username;

		do {
			username = "dummy-" + level.getRandom().nextInt(1_000_000_000, Integer.MAX_VALUE);
		} while (players.getPlayerByName(username) != null);
		return Dummy.create(username, level, position, rotation);
	}

	/**
	 * Creates and spawns a dummy standing on the bottom center of the block at the position.
	 */
	public static Dummy create(String username, ServerLevel level, Vec3 position, Vec2 rotation) {
		position = Vec3.atBottomCenterOf(BlockPos.containing(position));
		MinecraftServer server = level.getServer();
		GameProfile profile = new GameProfile(UUID.randomUUID(), username);
		ClientInformation clientInformation = ClientInformation.createDefault();
		Dummy instance = new Dummy(server, level, profile, clientInformation, position, rotation);
		FakeConnection connection = new FakeConnection(PacketFlow.SERVERBOUND);
		CommonListenerCookie cookie = new CommonListenerCookie(profile, 0, clientInformation, false);
		level.getServer().getPlayerList().placeNewPlayer(connection, instance, cookie);
		instance.teleportTo(level, position.x, position.y, position.z, Set.of(), rotation.y, rotation.x, true);
		instance.setHealth(20);
		instance.unsetRemoved();
		instance.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
		server.getPlayerList().broadcastAll(new ClientboundRotateHeadPacket(instance, (byte) (instance.yHeadRot * 256 / 360)), level.dimension());
		server.getPlayerList().broadcastAll(ClientboundEntityPositionSyncPacket.of(instance), level.dimension());
		instance.entityData.set(DATA_PLAYER_MODE_CUSTOMISATION, (byte) 0x7f);
		return instance;
	}

	public Dummy(
			MinecraftServer server,
			ServerLevel level,
			GameProfile gameProfile,
			ClientInformation clientInformation,
			Vec3 originalSpawnPosition,
			Vec2 originalSpawnRotation) {
		super(server, level, gameProfile, clientInformation);
		this.ward$originalSpawnPosition = originalSpawnPosition;
		this.ward$originalSpawnRotation = originalSpawnRotation;
	}

	public void leave(Component reason) {
		MinecraftServer server = Objects.requireNonNull(this.level().getServer());
		server.getPlayerList().remove(this);
		this.connection.onDisconnect(new DisconnectionDetails(reason));
	}

	public void respawn() {
		MinecraftServer server = Objects.requireNonNull(this.level().getServer());
		server.getPlayerList().respawn(this, false, Entity.RemovalReason.KILLED);
	}

	public boolean useItem() {
		for (InteractionHand hand : InteractionHand.values()) {
			ItemStack handItem = getItemInHand(hand);

			if (gameMode.useItem(this, level(), handItem, hand).consumesAction()) {
				return true;
			}
		}

		return false;
	}

	public boolean useOnBlock(Vec3 pos, Direction direction) {
		for (InteractionHand hand : InteractionHand.values()) {
			ItemStack handItem = getItemInHand(hand);
			BlockHitResult blockHit = new BlockHitResult(pos, direction, BlockPos.containing(pos), false);

			if (gameMode.useItemOn(this, level(), handItem, hand, blockHit).consumesAction()) {
				// The trigger normally fires from the network handler, which dummies bypass
				CriteriaTriggers.ANY_BLOCK_USE.trigger(this, blockHit.getBlockPos(), handItem);
				swing(hand);
				return true;
			}
		}

		return false;
	}

	public boolean useOnEntity(Entity entity, Vec3 location) {
		for (InteractionHand hand : InteractionHand.values()) {
			ItemStack used = getItemInHand(hand).copy();

			if (interactOn(entity, hand, location) instanceof InteractionResult.Success success) {
				// The trigger normally fires from the network handler, which dummies bypass
				CriteriaTriggers.PLAYER_INTERACTED_WITH_ENTITY.trigger(
						this,
						success.wasItemInteraction() ? used : ItemStack.EMPTY,
						entity);
				return true;
			}
		}

		return false;
	}

	@Override
	public String getIpAddress() {
		return "127.0.0.1";
	}

	@Override
	public BlockPos adjustSpawnLocation(ServerLevel level, BlockPos spawnSuggestion) {
		// Return exact spawn position without searching for safe spots
		return BlockPos.containing(this.ward$originalSpawnPosition);
	}

	@Override
	public void onEquipItem(EquipmentSlot slot, ItemStack previous, ItemStack stack) {
		// Suppress equipment change packets while consuming items.
		if (!isUsingItem()) {
			super.onEquipItem(slot, previous, stack);
		}
	}

	@Override
	public void die(DamageSource cause) {
		super.die(cause);

		if (this.level().getGameRules().get(GameRules.IMMEDIATE_RESPAWN)) {
			MinecraftServer server = Objects.requireNonNull(this.level().getServer());
			server.schedule(new TickTask(server.getTickCount(), () -> this.connection.handleClientCommand(
					new ServerboundClientCommandPacket(ServerboundClientCommandPacket.Action.PERFORM_RESPAWN))));
		}
	}

	@Override
	public void tick() {
		// Every 10 ticks: prevent "moved too quickly" disconnect checks
		if (this.level().getServer().getTickCount() % 10 == 0) {
			this.connection.resetPosition();
			this.level().getChunkSource().move(this);
		}

		try {
			super.tick();
			this.doTick();
		} catch (NullPointerException _) {
			// NPE can occur during respawn transition when dummy is in inconsistent state
		}
	}
}
