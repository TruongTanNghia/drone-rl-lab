// Mô hình vật lý quadcopter huấn luyện (chế độ góc / "angle mode" như drone tập lái):
// cần pitch/roll đặt góc nghiêng mục tiêu, cần yaw đặt tốc độ quay, cần ga đặt lực đẩy quanh mức treo.
// Hệ trục Three.js: y lên; heading ψ = 0 nhìn về −z.

export type Vec3 = { x: number; y: number; z: number };
export type Inputs = { thr: number; yaw: number; pitch: number; roll: number }; // mỗi giá trị trong [−1, 1]

export type DroneState = {
  pos: Vec3;
  vel: Vec3;
  roll: number; // rad, dương = nghiêng phải
  pitch: number; // rad, dương = chúi mũi (bay tới)
  yaw: number; // rad
  yawRate: number;
  onGround: boolean;
  crashed: boolean;
  crashReason: string;
  t: number;
  touchdownSpeed: number; // m/s lúc chạm đất lần gần nhất
  landings: number;
};

export const PARAMS = {
  mass: 0.6, // kg, cỡ drone tập lái
  g: 9.81,
  maxTilt: (30 * Math.PI) / 180,
  tau: 0.14, // hằng số thời gian đáp ứng góc (s)
  yawRateMax: 2.4, // rad/s
  thrGain: 0.45, // ga ±1 → lực đẩy = trọng lượng × (1 ± 0.45) → leo tối đa ≈ 3,5 m/s
  drag: 0.6, // cản ngang (1/s) → nghiêng 30° đạt ≈ 8 m/s, 15° ≈ 4 m/s
  dragV: 1.2, // cản dọc (1/s)
  groundY: 0.03,
  crashSpeed: 2.0, // m/s chạm đất gây rơi
  crashTilt: (32 * Math.PI) / 180,
};

export const ZERO: Inputs = { thr: 0, yaw: 0, pitch: 0, roll: 0 };

export function initialState(pos: Vec3 = { x: 0, y: PARAMS.groundY, z: 0 }, yaw = 0): DroneState {
  return { pos: { ...pos }, vel: { x: 0, y: 0, z: 0 }, roll: 0, pitch: 0, yaw, yawRate: 0, onGround: pos.y <= PARAMS.groundY + 1e-6, crashed: false, crashReason: "", t: 0, touchdownSpeed: 0, landings: 0 };
}

export function tilt(s: DroneState): number {
  return Math.acos(Math.cos(s.roll) * Math.cos(s.pitch));
}

export function hspeed(s: DroneState): number {
  return Math.hypot(s.vel.x, s.vel.z);
}

/** Một bước vật lý (dt nhỏ, ~1/240 s). Thay đổi trực tiếp `s`. */
export function step(s: DroneState, u: Inputs, dt: number, wind?: Vec3): void {
  if (s.crashed) return;
  const P = PARAMS;
  s.t += dt;
  const k = Math.min(1, dt / P.tau);
  const thrust = P.mass * P.g * (1 + P.thrGain * u.thr);

  if (s.onGround) {
    // trên mặt đất: chỉ cất cánh khi lực đẩy vượt trọng lượng
    if (thrust <= P.mass * P.g * 1.03) {
      s.vel.x = s.vel.y = s.vel.z = 0;
      s.roll += (0 - s.roll) * k;
      s.pitch += (0 - s.pitch) * k;
      s.yawRate = 0;
      return;
    }
    s.onGround = false;
  }

  s.roll += (u.roll * P.maxTilt - s.roll) * k;
  s.pitch += (u.pitch * P.maxTilt - s.pitch) * k;
  s.yawRate = u.yaw * P.yawRateMax;
  s.yaw += s.yawRate * dt;

  const fwd = { x: -Math.sin(s.yaw), z: -Math.cos(s.yaw) };
  const right = { x: Math.cos(s.yaw), z: -Math.sin(s.yaw) };
  const a = thrust / P.mass;
  const ax = a * (Math.sin(s.pitch) * fwd.x + Math.sin(s.roll) * right.x) - P.drag * s.vel.x + (wind?.x ?? 0);
  const az = a * (Math.sin(s.pitch) * fwd.z + Math.sin(s.roll) * right.z) - P.drag * s.vel.z + (wind?.z ?? 0);
  const ay = a * Math.cos(s.roll) * Math.cos(s.pitch) - P.g - P.dragV * s.vel.y + (wind?.y ?? 0);

  s.vel.x += ax * dt;
  s.vel.y += ay * dt;
  s.vel.z += az * dt;
  s.pos.x += s.vel.x * dt;
  s.pos.y += s.vel.y * dt;
  s.pos.z += s.vel.z * dt;

  if (s.pos.y <= P.groundY) {
    s.pos.y = P.groundY;
    s.touchdownSpeed = Math.max(0, -s.vel.y);
    if (s.touchdownSpeed > P.crashSpeed) {
      s.crashed = true;
      s.crashReason = `chạm đất quá mạnh (${s.touchdownSpeed.toFixed(1)} m/s)`;
    } else if (tilt(s) > P.crashTilt) {
      s.crashed = true;
      s.crashReason = `chạm đất khi nghiêng ${((tilt(s) * 180) / Math.PI).toFixed(0)}°`;
    } else if (hspeed(s) > 1.5) {
      s.crashed = true;
      s.crashReason = `chạm đất khi còn trượt ngang ${hspeed(s).toFixed(1)} m/s`;
    } else {
      s.onGround = true;
      s.landings += 1;
      s.vel.x = s.vel.y = s.vel.z = 0;
    }
  }
}

/** Gió giật kiểu Ornstein–Uhlenbeck (dùng cho bài nâng cao). */
export class Gust {
  private g: Vec3 = { x: 0, y: 0, z: 0 };
  constructor(private sigma = 0, private tau = 1.5) {}
  set(sigma: number) {
    this.sigma = sigma;
  }
  sample(dt: number): Vec3 {
    if (this.sigma <= 0) return { x: 0, y: 0, z: 0 };
    const q = this.sigma * Math.sqrt((2 / this.tau) * dt);
    const n = () => (Math.random() + Math.random() + Math.random() - 1.5) * 2;
    this.g.x += (-this.g.x / this.tau) * dt + q * n();
    this.g.z += (-this.g.z / this.tau) * dt + q * n();
    return { x: this.g.x, y: 0, z: this.g.z };
  }
}
