"""In các giá trị thực của gym-pybullet-drones (SPEED_LIMIT, IMG_RES, tần số...) để ghi vào docs/library_notes.md."""
import numpy as np

from gym_pybullet_drones.envs.HoverAviary import HoverAviary
from gym_pybullet_drones.utils.enums import ActionType, ObservationType

env = HoverAviary(act=ActionType.VEL, obs=ObservationType.KIN, gui=False)
print("MAX_SPEED_KMH", env.MAX_SPEED_KMH, "-> SPEED_LIMIT (m/s) =", env.SPEED_LIMIT)
print("CTRL_FREQ", env.CTRL_FREQ, "PYB_FREQ", env.PYB_FREQ, "PYB_STEPS_PER_CTRL", env.PYB_STEPS_PER_CTRL)
print("obs space", env.observation_space.shape, "act space", env.action_space.shape, "ACTION_BUFFER_SIZE", env.ACTION_BUFFER_SIZE)
print("M", env.M, "L", env.L, "KF", env.KF, "KM", env.KM, "HOVER_RPM", env.HOVER_RPM, "MAX_RPM", env.MAX_RPM)
print("COLLISION_R", env.COLLISION_R, "COLLISION_H", env.COLLISION_H, "COLLISION_Z_OFFSET", env.COLLISION_Z_OFFSET)
print("EPISODE_LEN_SEC", env.EPISODE_LEN_SEC, "TARGET_POS", env.TARGET_POS)
obs, info = env.reset(seed=0)
print("reset obs[:12]", np.round(obs[0, :12], 3), "info", info)
env.close()
env2 = HoverAviary(act=ActionType.VEL, obs=ObservationType.RGB, gui=False)
print("IMG_RES", env2.IMG_RES, "IMG_FRAME_PER_SEC", env2.IMG_FRAME_PER_SEC, "IMG_CAPTURE_FREQ", env2.IMG_CAPTURE_FREQ, "obs", env2.observation_space.shape)
env2.close()
