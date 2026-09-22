#!/usr/bin/env python3
"""Oracle Cloud 免费 ARM (Ampere A1) 实例自动抢购脚本。

背景：免费 ARM (VM.Standard.A1.Flex) 在亚太热门区常年 "Out of host capacity"，
      纯手动点击基本抢不到。本脚本用官方 OCI SDK 每 N 秒轮询创建请求，
      一有放量立刻抢到并退出。

前置（只需做一次）：
    pip install oci oci-cli
    oci setup config        # 交互式生成 ~/.oci/config（填 tenancy/user/fingerprint/私钥/region）
    # 或在控制台「我的概要文件 → API 密钥」创建，把配置粘进 ~/.oci/config

用法：
    python oracle-grab-arm.py                                  # 4 OCPU / 24GB，45 秒一轮
    python oracle-grab-arm.py --ocpus 2 --memory 12 --interval 30
    python oracle-grab-arm.py --region ap-tokyo-1
    python oracle-grab-arm.py --ssh-key-file ~/.ssh/linkedin-auto-deploy.pub

说明：
    - 在该区域的**所有可用域(AD)** 轮流尝试（容量是按 AD 释放的）
    - 自动挑选 ARM 兼容的 Ubuntu 镜像 + 第一个可用子网
    - 抢到后打印实例 OCID 与公网 IP，随即退出
    - Ctrl+C 随时停止（不会产生费用：免费额度内不扣费，未创建成功更无影响）
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import oci
except ImportError:
    sys.exit("缺少依赖：pip install oci")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pick_arm_image(compute, compartment: str, shape: str):
    """挑一个 ARM 兼容的 Ubuntu 22.04 镜像。"""
    images = compute.list_images(
        compartment_id=compartment,
        operating_system="Canonical Ubuntu",
        shape=shape,
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    for img in images:
        name = (img.display_name or "").lower()
        if "aarch64" in name and ("22.04" in name or "24.04" in name):
            return img
    for img in images:  # 退而求其次：任何 aarch64
        if "aarch64" in (img.display_name or "").lower():
            return img
    return None


def pick_subnet(network, compartment: str):
    """挑第一个子网（优先 public）。"""
    vcns = network.list_vcns(compartment_id=compartment).data
    if not vcns:
        return None
    subnets = network.list_subnets(compartment_id=compartment, vcn_id=vcns[0].id).data
    if not subnets:
        return None
    for sn in subnets:
        if "public" in (sn.display_name or "").lower():
            return sn
    return subnets[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Oracle 免费 ARM 实例自动抢购")
    ap.add_argument("--profile", default="DEFAULT", help="~/.oci/config 中的配置名")
    ap.add_argument("--region", default="", help="覆盖 config 里的 region（如 ap-tokyo-1 / us-phoenix-1）")
    ap.add_argument("--ocpus", type=float, default=4.0, help="OCPU 数（免费上限 4）")
    ap.add_argument("--memory", type=float, default=24.0, help="内存 GB（免费上限 24）")
    ap.add_argument("--interval", type=int, default=45, help="轮询间隔秒（建议 30-60，太快会限流）")
    ap.add_argument("--display-name", default="linkedin-auto", help="实例名")
    ap.add_argument("--ssh-key-file", default="", help="SSH 公钥文件（默认 ~/.ssh/id_ed25519.pub）")
    args = ap.parse_args()

    config = oci.config.from_file(profile_name=args.profile)
    if args.region:
        config["region"] = args.region
    oci.config.validate_config(config)
    compartment = config["tenancy"]

    key_path = Path(args.ssh_key_file).expanduser() if args.ssh_key_file else Path.home() / ".ssh" / "id_ed25519.pub"
    if not key_path.exists():
        return sys.exit(f"找不到 SSH 公钥: {key_path}（用 --ssh-key-file 指定）")
    ssh_key = key_path.read_text(encoding="utf-8").strip()

    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)
    network = oci.core.VirtualNetworkClient(config)

    ads = identity.list_availability_domains(compartment_id=compartment).data
    if not ads:
        return sys.exit("该区域没有可用域")

    image = pick_arm_image(compute, compartment, "VM.Standard.A1.Flex")
    if image is None:
        return sys.exit("没找到 ARM(aarch64) Ubuntu 镜像，请确认区域/权限")
    subnet = pick_subnet(network, compartment)
    if subnet is None:
        return sys.exit("没找到可用子网，请先在控制台创建 VCN/子网")

    log(f"区域: {config['region']}")
    log(f"可用域: {', '.join(a.name for a in ads)}")
    log(f"镜像: {image.display_name}")
    log(f"子网: {subnet.display_name}")
    log(f"配置: {args.ocpus} OCPU / {args.memory} GB  |  每 {args.interval}s 轮询一次")
    log("开始抢购…（Ctrl+C 停止）")

    attempt = 0
    while True:
        for ad in ads:
            attempt += 1
            details = oci.core.models.LaunchInstanceDetails(
                availability_domain=ad.name,
                compartment_id=compartment,
                display_name=args.display_name,
                shape="VM.Standard.A1.Flex",
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=args.ocpus, memory_in_gbs=args.memory
                ),
                source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=image.id),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet.id, assign_public_ip=True
                ),
                metadata={"ssh_authorized_keys": ssh_key},
            )
            try:
                inst = compute.launch_instance(details).data
                log(f"🎉 抢到了！实例: {inst.display_name} ({inst.id})")
                log(f"    可用域: {ad.name}  状态: {inst.lifecycle_state}")
                log("    稍等 1-2 分钟，到控制台看公网 IP，然后就可以部署了。")
                return 0
            except oci.exceptions.ServiceError as e:
                msg = str(e.message or "")
                if "capacity" in msg.lower() or "Out of host capacity" in msg:
                    log(f"第 {attempt} 次: {ad.name} 无容量，继续…")
                elif e.status == 429:
                    log("请求过于频繁(429)，加大 --interval 或稍后再试")
                else:
                    log(f"⚠️ 出错({e.status}): {msg[:120]}")
                    if e.status in (401, 404):
                        return 1
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已停止。")
