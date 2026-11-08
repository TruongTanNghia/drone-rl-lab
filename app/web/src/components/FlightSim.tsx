"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { Gust, hspeed, initialState, step, tilt, PARAMS, ZERO, type DroneState, type Inputs } from "@/lib/sim/drone";
import { grade, saveAttempt, type Report } from "@/lib/sim/grading";
import { DEFAULT_CFG, KeyInput, loadCfg, readGamepad, saveCfg, type InputCfg } from "@/lib/sim/input";
import { createTracker, LESSONS, type Lesson, type Progress, type Sample } from "@/lib/sim/lessons";

type Hud = {
  alt: number; vs: number; hs: number; tiltDeg: number; heading: number; t: number;
  u: Inputs; source: "gamepad" | "keyboard" | "none"; padId: string; raw: number[];
  prog: Progress | null; onGround: boolean; crashed: boolean; warn: string[];
};

const PHYS_DT = 1 / 240;
const SAMPLE_HZ = 20;

export default function FlightSim({ lesson }: { lesson: Lesson }) {
  const mount = useRef<HTMLDivElement>(null);
  const [hud, setHud] = useState<Hud | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [camMode, setCamMode] = useState<"chase" | "los" | "top">("chase");
  const [cfg, setCfg] = useState<InputCfg>(DEFAULT_CFG);
  const [showCfg, setShowCfg] = useState(false);
  const [wind, setWind] = useState(0);
  const [runKey, setRunKey] = useState(0);
  const camRef = useRef(camMode);
  const cfgRef = useRef(cfg);
  const windRef = useRef(wind);
  const startedRef = useRef(false);

  useEffect(() => {
    camRef.current = camMode;
  }, [camMode]);
  useEffect(() => {
    cfgRef.current = cfg;
  }, [cfg]);
  useEffect(() => {
    windRef.current = wind;
  }, [wind]);
  useEffect(() => {
    const id = setTimeout(() => setCfg(loadCfg()), 0);
    return () => clearTimeout(id);
  }, []);

  const restart = useCallback(() => {
    setReport(null);
    setRunKey((k) => k + 1);
  }, []);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;
    // ------------------------------------------------------------ cảnh
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xb9d3e6);
    scene.fog = new THREE.Fog(0xb9d3e6, 40, 140);
    const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 400);
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xdfefff, 0x6b7a5a, 0.9));
    const sun = new THREE.DirectionalLight(0xfff2d8, 1.6);
    sun.position.set(12, 20, 8);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = sun.shadow.camera.bottom = -14;
    sun.shadow.camera.right = sun.shadow.camera.top = 14;
    sun.shadow.camera.far = 60;
    scene.add(sun);

    // mặt sân tập: cỏ + lưới 1 m
    const gc = document.createElement("canvas");
    gc.width = gc.height = 256;
    const g2 = gc.getContext("2d")!;
    g2.fillStyle = "#6f9a5a";
    g2.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 1800; i++) {
      g2.fillStyle = `rgba(${40 + Math.random() * 40},${90 + Math.random() * 60},${30 + Math.random() * 30},0.35)`;
      g2.fillRect(Math.random() * 256, Math.random() * 256, 2, 2);
    }
    g2.strokeStyle = "rgba(255,255,255,0.22)";
    g2.lineWidth = 2;
    g2.strokeRect(0, 0, 256, 256);
    const gt = new THREE.CanvasTexture(gc);
    gt.wrapS = gt.wrapT = THREE.RepeatWrapping;
    gt.repeat.set(120, 120);
    gt.anisotropy = 8;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), new THREE.MeshLambertMaterial({ map: gt }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // bãi đáp chữ H
    const pc = document.createElement("canvas");
    pc.width = pc.height = 256;
    const p2 = pc.getContext("2d")!;
    p2.fillStyle = "#2b2b2b";
    p2.beginPath();
    p2.arc(128, 128, 126, 0, Math.PI * 2);
    p2.fill();
    p2.strokeStyle = "#f2d13b";
    p2.lineWidth = 10;
    p2.beginPath();
    p2.arc(128, 128, 112, 0, Math.PI * 2);
    p2.stroke();
    p2.fillStyle = "#f2f2f2";
    p2.font = "bold 150px sans-serif";
    p2.textAlign = "center";
    p2.textBaseline = "middle";
    p2.fillText("H", 128, 136);
    const pad = new THREE.Mesh(new THREE.CircleGeometry(1.0, 48), new THREE.MeshLambertMaterial({ map: new THREE.CanvasTexture(pc) }));
    pad.rotation.x = -Math.PI / 2;
    pad.position.y = 0.005;
    pad.receiveShadow = true;
    scene.add(pad);

    // cột cờ / cây làm mốc không gian
    const poleMat = new THREE.MeshLambertMaterial({ color: 0xd8d8d8 });
    const flagMat = new THREE.MeshLambertMaterial({ color: 0xe8552f, side: THREE.DoubleSide });
    for (const [x, z] of [[-8, -8], [8, -8], [8, 8], [-8, 8]] as [number, number][]) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 3, 8), poleMat);
      pole.position.set(x, 1.5, z);
      pole.castShadow = true;
      scene.add(pole);
      const flag = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 0.35), flagMat);
      flag.position.set(x + 0.3, 2.8, z);
      scene.add(flag);
    }
    const treeMat = new THREE.MeshLambertMaterial({ color: 0x3f7a3a });
    const trunkMat = new THREE.MeshLambertMaterial({ color: 0x6b4a2b });
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2, r = 22 + (i % 3) * 5;
      const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.18, 1.6, 6), trunkMat);
      tr.position.set(Math.cos(a) * r, 0.8, Math.sin(a) * r);
      const cr = new THREE.Mesh(new THREE.ConeGeometry(1.2 + (i % 2) * 0.5, 3 + (i % 3), 7), treeMat);
      cr.position.set(Math.cos(a) * r, 3, Math.sin(a) * r);
      cr.castShadow = true;
      scene.add(tr, cr);
    }

    // vòng mục tiêu
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xf2a93b, transparent: true, opacity: 0.85 });
    const ringNextMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 });
    const ringOkMat = new THREE.MeshBasicMaterial({ color: 0x7bd88f, transparent: true, opacity: 0.9 });
    const ring = new THREE.Mesh(new THREE.TorusGeometry(lesson.hoverRadius ?? 0.8, 0.035, 10, 64), ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.visible = false;
    scene.add(ring);
    const ringNext = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.025, 8, 48), ringNextMat);
    ringNext.rotation.x = Math.PI / 2;
    ringNext.visible = false;
    scene.add(ringNext);
    const ringPost = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 1, 6), new THREE.MeshBasicMaterial({ color: 0xf2a93b, transparent: true, opacity: 0.4 }));
    ringPost.visible = false;
    scene.add(ringPost);
    // các vòng waypoint còn lại (mờ)
    const wpMarks: THREE.Mesh[] = [];
    if (lesson.waypoints) {
      for (const w of lesson.waypoints) {
        const m = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.015, 6, 40), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.12 }));
        m.rotation.x = Math.PI / 2;
        m.position.set(w.x, w.y, w.z);
        scene.add(m);
        wpMarks.push(m);
      }
    }

    // drone
    const drone = new THREE.Group();
    scene.add(drone);
    const model = new THREE.Group();
    model.scale.setScalar(3.2);
    drone.add(model);
    const rotors: THREE.Mesh[] = [];
    const rotorMat = new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.35 });
    const buildFallback = () => {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.02, 0.06), new THREE.MeshLambertMaterial({ color: 0x334455 }));
      g.add(body);
      for (const [sx, sz] of [[1, 1], [1, -1], [-1, -1], [-1, 1]]) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.006, 0.01), new THREE.MeshLambertMaterial({ color: 0x889099 }));
        arm.position.set(sx * 0.03, 0, sz * 0.03);
        arm.rotation.y = Math.atan2(-sz, sx);
        g.add(arm);
        const r = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.023, 0.002, 18), rotorMat);
        r.position.set(sx * 0.0397, 0.012, sz * 0.0397);
        g.add(r);
        rotors.push(r);
      }
      return g;
    };
    model.add(buildFallback());
    new GLTFLoader().load(
      "/models/cf2.glb",
      (gltf) => {
        const obj = gltf.scene;
        obj.traverse((o) => {
          const m = o as THREE.Mesh;
          if (m.isMesh) {
            const col = (m.material as THREE.MeshStandardMaterial)?.color ?? new THREE.Color(0x8899aa);
            m.material = new THREE.MeshLambertMaterial({ color: col });
            m.castShadow = true;
          }
        });
        obj.rotation.x = -Math.PI / 2; // cf2.dae có trục z lên
        model.clear();
        rotors.length = 0;
        model.add(obj);
        for (const [sx, sz] of [[1, 1], [1, -1], [-1, -1], [-1, 1]]) {
          const r = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.023, 0.002, 18), rotorMat);
          r.position.set(sx * 0.0397, 0.012, sz * 0.0397);
          model.add(r);
          rotors.push(r);
        }
      },
      undefined,
      () => {},
    );
    // mũi drone (đèn) để biết hướng
    const nose = new THREE.Mesh(new THREE.SphereGeometry(0.02, 8, 8), new THREE.MeshBasicMaterial({ color: 0xff3b3b }));
    nose.position.set(0, 0.02, -0.16);
    drone.add(nose);
    const shadowDisc = new THREE.Mesh(new THREE.CircleGeometry(0.22, 24), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.3 }));
    shadowDisc.rotation.x = -Math.PI / 2;
    shadowDisc.position.y = 0.006;
    scene.add(shadowDisc);
    // vệt bay
    const trailPts = new Float32Array(600 * 3);
    const trailGeo = new THREE.BufferGeometry();
    trailGeo.setAttribute("position", new THREE.BufferAttribute(trailPts, 3));
    trailGeo.setDrawRange(0, 0);
    const trail = new THREE.Line(trailGeo, new THREE.LineBasicMaterial({ color: 0xf2a93b, transparent: true, opacity: 0.6 }));
    scene.add(trail);
    let trailN = 0, trailAcc = 0;

    // ------------------------------------------------------------ trạng thái bài tập
    const startPos = lesson.startAirborne ? { x: 0.8, y: lesson.altitude, z: 0.8 } : { x: 0, y: PARAMS.groundY, z: 0 };
    const s: DroneState = initialState(startPos, 0);
    const tracker = createTracker(lesson);
    const keys = new KeyInput();
    keys.attach();
    const gust = new Gust(0);
    const samples: Sample[] = [];
    let sampleAcc = 0;
    let prog: Progress | null = tracker.update(s, ZERO, 0); // hiện vòng mục tiêu ngay từ đầu
    let finished = false;
    let finishAt = 0;
    const warnLog: { t: number; msg: string }[] = [];
    let u: Inputs = { ...ZERO };
    let source: Hud["source"] = "none";
    let padId = "";
    let raw: number[] = [];
    const smoothCam = new THREE.Vector3(0, 2.5, 6);
    let lastTs = performance.now();
    let acc = 0;
    let hudAcc = 0;
    let alive = true;
    // cảnh báo tức thời: gắt cần / nghiêng lớn
    let lastU: Inputs = { ...ZERO };
    let warnAcc = 0;

    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    const finish = (p: Progress) => {
      finished = true;
      finishAt = s.t;
      const rep = grade(lesson, samples, p, { touchdown: s.touchdownSpeed });
      saveAttempt(rep);
      setReport(rep);
    };

    const frame = (ts: number) => {
      if (!alive) return;
      requestAnimationFrame(frame);
      const dtReal = Math.min(0.1, (ts - lastTs) / 1000);
      lastTs = ts;

      // ---- đọc cần
      const gp = readGamepad(cfgRef.current);
      const ku = keys.read(dtReal);
      if (gp && (Math.abs(gp.u.thr) + Math.abs(gp.u.yaw) + Math.abs(gp.u.pitch) + Math.abs(gp.u.roll) > 0 || !keys.active)) {
        u = gp.u;
        source = "gamepad";
        padId = gp.id;
        raw = gp.raw;
      } else {
        u = ku;
        source = keys.active ? "keyboard" : gp ? "gamepad" : "none";
        if (gp) {
          padId = gp.id;
          raw = gp.raw;
        }
      }
      if (!startedRef.current && (Math.abs(u.thr) > 0.1 || Math.abs(u.pitch) > 0.1 || Math.abs(u.roll) > 0.1 || Math.abs(u.yaw) > 0.1)) startedRef.current = true;

      // ---- vật lý 240 Hz (chỉ chạy khi đã bắt đầu và chưa xong)
      if (startedRef.current && !finished) {
        gust.set(windRef.current);
        acc += dtReal;
        let n = 0;
        while (acc >= PHYS_DT && n < 24) {
          step(s, u, PHYS_DT, gust.sample(PHYS_DT));
          acc -= PHYS_DT;
          n++;
        }
        prog = tracker.update(s, u, dtReal);
        // mẫu 20 Hz cho chấm điểm
        sampleAcc += dtReal;
        if (sampleAcc >= 1 / SAMPLE_HZ) {
          sampleAcc = 0;
          samples.push({ t: s.t, u: { ...u }, pos: { ...s.pos }, vel: { ...s.vel }, roll: s.roll, pitch: s.pitch, yaw: s.yaw, inZone: prog.inZone });
        }
        // cảnh báo tức thời
        warnAcc += dtReal;
        if (warnAcc >= 0.1) {
          const rate = Math.max(Math.abs(u.pitch - lastU.pitch), Math.abs(u.roll - lastU.roll), Math.abs(u.thr - lastU.thr)) / warnAcc;
          if (rate > 5 && !s.onGround) warnLog.push({ t: s.t, msg: "Gắt cần!" });
          if (tilt(s) > (24 * Math.PI) / 180) warnLog.push({ t: s.t, msg: "Nghiêng lớn" });
          if (s.vel.y < -1.6 && s.pos.y < 2) warnLog.push({ t: s.t, msg: "Hạ quá nhanh!" });
          lastU = { ...u };
          warnAcc = 0;
        }
        if (prog.status !== "running") finish(prog);
      } else if (finished && !s.crashed) {
        // sau khi xong: drone đứng yên tại chỗ (trên không thì giữ hover)
      }

      // ---- cập nhật cảnh
      drone.position.set(s.pos.x, s.pos.y, s.pos.z);
      drone.rotation.set(0, 0, 0);
      drone.rotateY(s.yaw);
      drone.rotateX(s.pitch); // chúi mũi về −z
      drone.rotateZ(-s.roll);
      shadowDisc.position.set(s.pos.x, 0.006, s.pos.z);
      const sh = Math.max(0.3, 1 - s.pos.y / 12);
      shadowDisc.scale.setScalar(sh);
      (shadowDisc.material as THREE.MeshBasicMaterial).opacity = 0.3 * sh;
      const spin = s.onGround && !startedRef.current ? 0 : s.crashed ? 0 : 0.5 + 0.6 * (1 + u.thr);
      rotors.forEach((r, i) => (r.rotation.y += (i % 2 ? 1 : -1) * spin));
      if (s.crashed) {
        drone.rotation.z = 0.6;
      }
      trailAcc += dtReal;
      if (trailAcc > 0.1 && !s.onGround) {
        trailAcc = 0;
        if (trailN < 600) {
          trailPts.set([s.pos.x, s.pos.y, s.pos.z], trailN * 3);
          trailN++;
        } else {
          trailPts.copyWithin(0, 3);
          trailPts.set([s.pos.x, s.pos.y, s.pos.z], 599 * 3);
        }
        trailGeo.setDrawRange(0, trailN);
        trailGeo.attributes.position.needsUpdate = true;
      }
      if (prog?.target) {
        ring.visible = true;
        ring.position.set(prog.target.x, prog.target.y, prog.target.z);
        ring.material = prog.inZone ? ringOkMat : ringMat;
        ringPost.visible = prog.target.y > 0.1;
        ringPost.position.set(prog.target.x, prog.target.y / 2, prog.target.z);
        ringPost.scale.y = prog.target.y;
        if (lesson.kind === "landing") ring.position.y = 0.02;
      }
      if (prog?.nextTarget) {
        ringNext.visible = true;
        ringNext.position.set(prog.nextTarget.x, prog.nextTarget.y, prog.nextTarget.z);
      } else ringNext.visible = false;
      if (prog && lesson.waypoints) wpMarks.forEach((m, i) => (m.visible = i > prog!.wpIndex));

      // ---- camera
      const mode = camRef.current;
      const dp = new THREE.Vector3(s.pos.x, s.pos.y, s.pos.z);
      if (mode === "chase") {
        const back = new THREE.Vector3(Math.sin(s.yaw), 0, Math.cos(s.yaw)).multiplyScalar(2.6);
        const want = dp.clone().add(back).add(new THREE.Vector3(0, 1.2, 0));
        smoothCam.lerp(want, 1 - Math.exp(-dtReal * 4));
        camera.position.copy(smoothCam);
        camera.lookAt(dp.x, dp.y + 0.1, dp.z);
      } else if (mode === "los") {
        camera.position.set(0, 1.65, 7.5);
        camera.lookAt(dp);
        camera.fov = THREE.MathUtils.clamp(60 - dp.distanceTo(camera.position) * 1.5, 25, 60);
        camera.updateProjectionMatrix();
      } else {
        camera.position.set(dp.x, Math.max(12, dp.y + 10), dp.z + 0.001);
        camera.lookAt(dp.x, 0, dp.z);
      }
      renderer.render(scene, camera);

      // ---- HUD 15 Hz
      hudAcc += dtReal;
      if (hudAcc > 1 / 15) {
        hudAcc = 0;
        const recentWarn = warnLog.filter((w) => s.t - w.t < 1.5).map((w) => w.msg);
        setHud({
          alt: s.pos.y - PARAMS.groundY, vs: s.vel.y, hs: hspeed(s), tiltDeg: (tilt(s) * 180) / Math.PI, heading: ((s.yaw * 180) / Math.PI + 360000) % 360, t: finished ? finishAt : s.t,
          u, source, padId, raw, prog, onGround: s.onGround, crashed: s.crashed, warn: Array.from(new Set(recentWarn)),
        });
      }
    };
    requestAnimationFrame(frame);

    return () => {
      alive = false;
      ro.disconnect();
      keys.detach();
      renderer.dispose();
      el.removeChild(renderer.domElement);
      startedRef.current = false;
    };
  }, [lesson, runKey]);

  const idx = LESSONS.findIndex((l) => l.id === lesson.id);
  const next = LESSONS[idx + 1];

  return (
    <div className="relative w-full" style={{ height: "calc(100vh - 56px)", minHeight: 560 }}>
      <div ref={mount} className="absolute inset-0" />

      {/* ── HUD trái: bài tập ── */}
      <div className="absolute left-4 top-4 w-[320px] flex flex-col gap-3 pointer-events-none">
        <div className="panel p-4 pointer-events-auto" style={{ background: "rgba(13,12,10,0.86)" }}>
          <div className="eyebrow">{lesson.id} · bài {idx + 1}/{LESSONS.length}</div>
          <div className="display text-[26px] leading-tight mt-1">{lesson.name}</div>
          <div className="text-mut text-[12.5px] mt-1">{lesson.goal}</div>
          <ul className="mt-3 flex flex-col gap-1 text-[12.5px]">
            {(hud?.prog?.checklist ?? lesson.steps.map((text) => ({ text, done: false }))).map((c, i) => (
              <li key={i} className={`flex gap-2 ${c.done ? "text-good" : "text-txt"}`}>
                <span className="mono">{c.done ? "✔" : "○"}</span>
                <span>{c.text}</span>
              </li>
            ))}
          </ul>
          <div className="bar mt-3">
            <i style={{ width: `${((hud?.prog?.fraction ?? 0) * 100).toFixed(0)}%` }} />
          </div>
          <div className="mt-3 text-[15px] text-acc2 min-h-[22px]">
            {hud?.prog ? hud.prog.instruction : "Gạt cần để bắt đầu"}
          </div>
        </div>
        {hud && hud.warn.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {hud.warn.map((w) => (
              <span key={w} className="chip chip-bad" style={{ background: "rgba(13,12,10,0.86)" }}>
                ⚠ {w}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── HUD phải: số đo + cần ── */}
      <div className="absolute right-4 top-4 w-[260px] flex flex-col gap-3">
        <div className="panel p-3" style={{ background: "rgba(13,12,10,0.86)" }}>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2">
            {[
              ["độ cao", `${(hud?.alt ?? 0).toFixed(2)} m`],
              ["tốc độ lên", `${(hud?.vs ?? 0).toFixed(2)} m/s`],
              ["tốc độ ngang", `${(hud?.hs ?? 0).toFixed(2)} m/s`],
              ["nghiêng", `${(hud?.tiltDeg ?? 0).toFixed(0)}°`],
              ["hướng", `${(hud?.heading ?? 0).toFixed(0)}°`],
              ["thời gian", `${(hud?.t ?? 0).toFixed(1)} s`],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="eyebrow" style={{ letterSpacing: "0.1em" }}>{k}</div>
                <div className="mono text-[17px]">{v}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="panel p-3" style={{ background: "rgba(13,12,10,0.86)" }}>
          <div className="flex justify-between items-baseline">
            <span className="eyebrow">cần điều khiển · mode {cfg.mode}</span>
            <span className={`chip ${hud?.source === "gamepad" ? "chip-good" : hud?.source === "keyboard" ? "chip-cyan" : ""}`} title={hud?.padId}>
              {hud?.source === "gamepad" ? "tay cầm" : hud?.source === "keyboard" ? "bàn phím" : "chưa có tín hiệu"}
            </span>
          </div>
          <div className="flex gap-3 mt-2 justify-center">
            <Stick x={cfg.mode === 2 ? hud?.u.yaw ?? 0 : hud?.u.yaw ?? 0} y={cfg.mode === 2 ? hud?.u.thr ?? 0 : hud?.u.pitch ?? 0} label={cfg.mode === 2 ? "ga / yaw" : "pitch / yaw"} />
            <Stick x={hud?.u.roll ?? 0} y={cfg.mode === 2 ? hud?.u.pitch ?? 0 : hud?.u.thr ?? 0} label={cfg.mode === 2 ? "pitch / roll" : "ga / roll"} />
          </div>
          <div className="mt-2 text-[11px] text-mut">Bàn phím: W/S ga · A/D yaw · mũi tên pitch/roll</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button className="btn" onClick={restart}>↺ Làm lại</button>
          <button className="btn" onClick={() => setCamMode((m) => (m === "chase" ? "los" : m === "los" ? "top" : "chase"))}>
            camera: {camMode === "chase" ? "đuổi" : camMode === "los" ? "phi công" : "trên cao"}
          </button>
          <button className="btn" onClick={() => setShowCfg((v) => !v)}>⚙ tay cầm</button>
          <label className="chip" style={{ cursor: "pointer" }}>
            gió <input type="range" min={0} max={3} step={0.5} value={wind} onChange={(e) => setWind(Number(e.target.value))} style={{ width: 70 }} /> {wind}
          </label>
        </div>
        {showCfg && <InputConfig cfg={cfg} raw={hud?.raw ?? []} padId={hud?.padId ?? ""} onChange={(c) => { setCfg(c); saveCfg(c); }} />}
      </div>

      {/* ── kết quả ── */}
      {report && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: "rgba(13,12,10,0.55)" }}>
          <div className="panel p-6 w-[720px] max-w-[92vw] max-h-[90vh] overflow-auto reveal" style={{ background: "rgba(13,12,10,0.96)" }}>
            <div className="flex items-start gap-5">
              <div>
                <div className="eyebrow">{lesson.id} · {report.status === "done" ? "hoàn thành" : "chưa đạt"}</div>
                <div className="display text-[64px] leading-none mt-1">
                  {report.score}
                  <span className="text-[22px] text-mut"> / 100</span>
                </div>
                <span className={`stamp ${report.score >= lesson.passScore ? "stamp-good" : "stamp-bad"} mt-3 inline-block`}>{report.score >= lesson.passScore ? "Đạt" : "Chưa đạt"}</span>
              </div>
              <div className="flex-1 grid grid-cols-4 gap-2">
                {([["control", "Điều khiển"], ["accuracy", "Chính xác"], ["stability", "Ổn định"], ["completion", "Hoàn thành"]] as const).map(([k, label]) => (
                  <div key={k} className="readout" style={{ borderLeft: "1px solid var(--line)", paddingLeft: 12 }}>
                    <div className="v">{report.parts[k]}<small>/25</small></div>
                    <div className="l eyebrow">{label}</div>
                  </div>
                ))}
              </div>
            </div>
            {report.reason && <div className="mt-3 text-bad text-[13px]">{report.reason}</div>}
            <div className="mt-4">
              <div className="eyebrow mb-2">Lỗi thao tác AI phát hiện</div>
              {report.flags.length === 0 ? (
                <div className="text-good text-[13px]">Không phát hiện lỗi thao tác.</div>
              ) : (
                <ul className="flex flex-col gap-2">
                  {report.flags.map((fl) => (
                    <li key={fl.code} className="border border-line p-2 text-[12.5px]">
                      <span className={`chip ${fl.severity >= 3 ? "chip-bad" : fl.severity === 2 ? "chip-acc" : ""}`}>{fl.name} · mức {fl.severity}</span>
                      <div className="mono text-mut mt-1">{fl.evidence}</div>
                      <div className="mt-1">→ {fl.tip}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="mt-3 mono text-[11px] text-dim flex flex-wrap gap-x-4">
              {Object.entries(report.features).map(([k, v]) => (
                <span key={k}>{k} {v}</span>
              ))}
            </div>
            <div className="mt-5 flex gap-2 flex-wrap">
              <button className="btn" onClick={restart}>↺ Làm lại bài này</button>
              {next && (
                <Link href={`/fly/${next.id}`} className="btn" style={{ borderColor: "var(--acc)", color: "var(--acc-2)" }}>
                  Bài tiếp: {next.id} {next.short} →
                </Link>
              )}
              <Link href="/" className="btn">Về danh sách bài</Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stick({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={84} height={84} viewBox="-1.1 -1.1 2.2 2.2">
        <rect x={-1} y={-1} width={2} height={2} fill="rgba(255,255,255,0.04)" stroke="var(--line-2)" strokeWidth={0.03} />
        <line x1={-1} y1={0} x2={1} y2={0} stroke="var(--line-2)" strokeWidth={0.02} />
        <line x1={0} y1={-1} x2={0} y2={1} stroke="var(--line-2)" strokeWidth={0.02} />
        <circle cx={x} cy={-y} r={0.13} fill="var(--acc)" />
      </svg>
      <span className="eyebrow" style={{ letterSpacing: "0.08em" }}>{label}</span>
    </div>
  );
}

function InputConfig({ cfg, raw, padId, onChange }: { cfg: InputCfg; raw: number[]; padId: string; onChange: (c: InputCfg) => void }) {
  const inv = (k: keyof InputCfg["invert"]) => onChange({ ...cfg, invert: { ...cfg.invert, [k]: !cfg.invert[k] } });
  return (
    <div className="panel p-3 text-[12px]" style={{ background: "rgba(13,12,10,0.92)" }}>
      <div className="eyebrow mb-2">Tay cầm: {padId || "chưa kết nối (bấm nút bất kỳ trên tay cầm)"}</div>
      <div className="flex gap-2 items-center flex-wrap">
        <span>Mode</span>
        <button className={`btn ${cfg.mode === 2 ? "text-acc2" : ""}`} onClick={() => onChange({ ...cfg, mode: 2 })}>2 (ga trái)</button>
        <button className={`btn ${cfg.mode === 1 ? "text-acc2" : ""}`} onClick={() => onChange({ ...cfg, mode: 1 })}>1 (ga phải)</button>
      </div>
      <div className="flex gap-2 items-center flex-wrap mt-2">
        <span>Đảo chiều</span>
        {(["thr", "yaw", "pitch", "roll"] as const).map((k) => (
          <button key={k} className={`btn ${cfg.invert[k] ? "text-acc2" : ""}`} onClick={() => inv(k)}>{k}</button>
        ))}
      </div>
      <div className="flex gap-2 items-center flex-wrap mt-2">
        <span>Trục</span>
        {(["lx", "ly", "rx", "ry"] as const).map((k) => (
          <label key={k} className="chip">
            {k} <input type="number" min={0} max={9} value={cfg.axes[k]} onChange={(e) => onChange({ ...cfg, axes: { ...cfg.axes, [k]: Number(e.target.value) } })} style={{ width: 36, background: "transparent", color: "inherit", border: 0 }} />
          </label>
        ))}
      </div>
      <div className="flex gap-2 items-center mt-2">
        <span>Deadzone</span>
        <input type="range" min={0} max={0.2} step={0.01} value={cfg.deadzone} onChange={(e) => onChange({ ...cfg, deadzone: Number(e.target.value) })} />
        <span className="mono">{cfg.deadzone.toFixed(2)}</span>
        <span>Expo</span>
        <input type="range" min={0} max={0.8} step={0.05} value={cfg.expo} onChange={(e) => onChange({ ...cfg, expo: Number(e.target.value) })} />
        <span className="mono">{cfg.expo.toFixed(2)}</span>
      </div>
      <div className="mono text-dim mt-2">trục thô: {raw.map((v, i) => `${i}:${v.toFixed(2)}`).join("  ") || "—"}</div>
    </div>
  );
}
