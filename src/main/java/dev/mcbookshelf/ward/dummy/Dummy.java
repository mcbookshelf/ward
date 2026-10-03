package dev.mcbookshelf.ward.dummy;

import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

import com.mojang.authlib.GameProfile;
import org.jspecify.annotations.Nullable;

import net.minecraft.advancements.triggers.CriteriaTriggers;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundEntityPositionSyncPacket;
import net.minecraft.network.protocol.game.ClientboundRotateHeadPacket;
import net.minecraft.network.protocol.game.ServerboundClientCommandPacket;
import net.minecraft.network.protocol.game.ServerboundPlayerInputPacket;
import net.minecraft.network.protocol.game.ServerboundPlayerLoadedPacket;
import net.minecraft.resources.ResourceKey;
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
import net.minecraft.world.entity.player.Input;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.SwingAnimation;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

/**
 * Inspired by the fake player of Carpet (https://github.com/gnembon/fabric-carpet).
 */
public class Dummy extends ServerPlayer {
	public final ResourceKey<Level> spawnDimension;
	public final Vec3 spawnPosition;
	public final Vec2 spawnRotation;

	public static Dummy create(ServerLevel level, Vec3 position, Vec2 rotation) {
		PlayerList players = level.getServer().getPlayerList();
		String username;

		do {
			username = "dummy-" + ThreadLocalRandom.current().nextInt(1_000_000_000, Integer.MAX_VALUE);
		} while (players.getPlayerByName(username) != null);
		return Dummy.create(username, level, position, rotation);
	}

	public static Dummy create(String username, ServerLevel level, Vec3 position, Vec2 rotation) {
		position = Vec3.atBottomCenterOf(BlockPos.containing(position));
		MinecraftServer server = level.getServer();
		GameProfile profile = new GameProfile(UUID.randomUUID(), username);
		CommonListenerCookie cookie = CommonListenerCookie.createInitial(profile, false);
		Dummy instance = new Dummy(server, level, profile, cookie.clientInformation(), level.dimension(), position, rotation);
		FakeConnection connection = new FakeConnection(PacketFlow.SERVERBOUND);
		server.getPlayerList().placeNewPlayer(connection, instance, cookie);
		instance.connection.handleAcceptPlayerLoad(new ServerboundPlayerLoadedPacket());
		instance.teleportTo(level, position.x, position.y, position.z, Set.of(), rotation.y, rotation.x, true);
		instance.setOnGround(true);
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
			ResourceKey<Level> spawnDimension,
			Vec3 spawnPosition,
			Vec2 spawnRotation) {
		super(server, level, gameProfile, clientInformation);
		this.spawnDimension = spawnDimension;
		this.spawnPosition = spawnPosition;
		this.spawnRotation = spawnRotation;
	}

	public void leave(Component reason) {
		this.connection.disconnect(reason);
	}

	public void respawn() {
		this.connection.handleClientCommand(new ServerboundClientCommandPacket(ServerboundClientCommandPacket.Action.PERFORM_RESPAWN));
		this.connection.handleAcceptPlayerLoad(new ServerboundPlayerLoadedPacket());
	}

	public void press(boolean sneak, boolean sprint) {
		Input input = this.getLastClientInput();
		this.connection.handlePlayerInput(new ServerboundPlayerInputPacket(
				new Input(input.forward(), input.backward(), input.left(), input.right(), input.jump(), sneak, sprint)));
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
		BlockHitResult blockHit = new BlockHitResult(pos, direction, BlockPos.containing(pos), false);

		for (InteractionHand hand : InteractionHand.values()) {
			ItemStack handItem = getItemInHand(hand);

			if (gameMode.useItemOn(this, level(), handItem, hand, blockHit).consumesAction()) {
				// The trigger normally fires from the network handler, which dummies bypass
				CriteriaTriggers.ANY_BLOCK_USE.trigger(this, blockHit.getBlockPos(), handItem);
				swing(hand, SwingAnimation.DEFAULT, false);
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
	public TeleportTransition findRespawnPositionAndUseSpawnBlock(boolean consumeSpawnBlock, TeleportTransition.PostTeleportTransition postTeleportTransition) {
		ServerLevel level = this.level().getServer().getLevel(this.spawnDimension);

		if (this.getRespawnConfig() == null && level != null) {
			return new TeleportTransition(level, this.spawnPosition, Vec3.ZERO, this.spawnRotation.y, this.spawnRotation.x, postTeleportTransition);
		}

		return super.findRespawnPositionAndUseSpawnBlock(consumeSpawnBlock, postTeleportTransition);
	}

	@Override
	public BlockPos adjustSpawnLocation(ServerLevel level, BlockPos spawnSuggestion) {
		return BlockPos.containing(this.spawnPosition);
	}

	@Override
	public void onEquipItem(EquipmentSlot slot, ItemStack previous, ItemStack stack) {
		if (!isUsingItem()) {
			super.onEquipItem(slot, previous, stack);
		}
	}

	@Override
	public void die(DamageSource cause) {
		super.die(cause);

		if (this.level().getGameRules().get(GameRules.IMMEDIATE_RESPAWN)) {
			MinecraftServer server = this.level().getServer();
			server.schedule(new TickTask(server.getTickCount(), () -> {
				if (server.getPlayerList().getPlayer(this.getUUID()) == this) {
					this.respawn();
				}
			}));
		}
	}

	@Override
	public @Nullable ServerPlayer teleport(TeleportTransition transition) {
		ServerPlayer player = super.teleport(transition);
		this.hasChangedDimension();
		return player;
	}

	@Override
	public void tick() {
		if (this.level().getServer().getTickCount() % 10 == 0) {
			this.connection.resetPosition();
			this.level().getChunkSource().move(this);
		}

		super.tick();
		this.doTick();
	}
}
