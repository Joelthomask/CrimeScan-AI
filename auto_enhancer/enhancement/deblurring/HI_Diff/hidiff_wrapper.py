import sys
from pathlib import Path
import os
import shutil
import subprocess
import cv2
from PIL import Image



from utils.temp_manager import get_temp_subpath
from utils.logger import get_logger, log_event
LOG = get_logger()


# ---------------- Configuration ---------------- #

HI_DIFF_ROOT = Path(__file__).resolve().parent

YAML_MILD   = HI_DIFF_ROOT / "options" / "test" / "RealBlur_J.yml"
YAML_STRONG = HI_DIFF_ROOT / "options" / "test" / "RealBlur_J.yml"
YAML_ULTRA  = HI_DIFF_ROOT / "options" / "test" / "RealBlur_J.yml"


class HiDiffWrapper:
    """
    HI-Diff Forensic Deblurring Executor (CLEAN)

    This class:
    ✔ Executes classical deblur (low)
    ✔ Executes HI-Diff (medium / high / ultra)
    ❌ Does NOT decide strength
    ❌ Does NOT analyze blur
    """

    def __init__(self, silent=False):
        self.silent = silent

        for p in [YAML_MILD, YAML_STRONG, YAML_ULTRA]:
            if not p.exists():
                raise FileNotFoundError(f"YAML config not found: {p}")

    # ------------------------------------------------
    # Internal logger
    # ------------------------------------------------

    def _log(self, layer, msg, level="INFO"):
        if not self.silent:
            log_event(layer, msg, level)

    # ========================================================
    # Classical micro deblur (LOW only)
    # ========================================================

    def _classical_deblur(self, input_img_path: str) -> str:
        img = cv2.imread(input_img_path)
        if img is None:
            raise ValueError("Failed to read image for classical deblur")

        blur = cv2.GaussianBlur(img, (0, 0), 1.0)
        sharp = cv2.addWeighted(img, 1.4, blur, -0.4, 0)

        out_path = get_temp_subpath("autoenhancement/blur") / Path(input_img_path).name
        cv2.imwrite(str(out_path), sharp)

        self._log("ENGINE", "Classical deblur applied (LOW)")
        return str(out_path)

    # ========================================================
    # HI-DIFF DATASET PREP
    # ========================================================

    def _create_temp_dataset(self, input_img_path: str) -> str:
        input_path = Path(input_img_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input image not found: {input_img_path}")

        input_dir = get_temp_subpath("datasets/test/RealBlur_J/input")
        target_dir = get_temp_subpath("datasets/test/RealBlur_J/target")

        img_name = input_path.stem + ".png"
        img = Image.open(input_path).convert("RGB")

        img.save(input_dir / img_name)
        img.save(target_dir / img_name)

        return img_name

    # ========================================================
    # YAML PATCH
    # ========================================================

    def _create_temp_yaml(self, base_yaml: Path, temp_yaml_path: Path):

        input_dir = get_temp_subpath("datasets/test/RealBlur_J/input")
        target_dir = get_temp_subpath("datasets/test/RealBlur_J/target")

        input_path_str = str(input_dir).replace("\\", "/")
        target_path_str = str(target_dir).replace("\\", "/")

        with open(base_yaml, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if "dataroot_gt:" in line:
                new_lines.append(f'    dataroot_gt: "{target_path_str}"\n')
            elif "dataroot_lq:" in line:
                new_lines.append(f'    dataroot_lq: "{input_path_str}"\n')
            else:
                new_lines.append(line)

        with open(temp_yaml_path, "w") as f:
            f.writelines(new_lines)

    # ========================================================
    # HI-DIFF EXECUTION
    # ========================================================

    def _run_hidiff(self, temp_yaml_path: Path):

        test_script = HI_DIFF_ROOT / "test.py"
        python_exe = sys.executable
        cmd = [python_exe, str(test_script), "-opt", str(temp_yaml_path)]

        self._log("ENGINE", "HI-DIFF inference started")
        result = subprocess.run(
            cmd,
            cwd=str(HI_DIFF_ROOT),
            capture_output=True,
            text=True
        )

        print("\n[HI-DIFF STDOUT]")
        print(result.stdout)

        print("\n[HI-DIFF STDERR]")
        print(result.stderr)

        print("\n[HI-DIFF RETURN CODE]")
        print(result.returncode)

        if result.returncode != 0:
            raise RuntimeError("HI-DIFF failed")


        self._log("ENGINE", "HI-DIFF inference completed")

    # ========================================================
    # MAIN ENTRY
    # ========================================================

    def enhance(self, input_img_path: str, strength="medium", silent=False) -> str:
        old = self.silent
        self.silent = silent or self.silent

        try:
            self._log("ENGINE", f"DEBLUR stage started → strength={strength}")

            # ---------- LOW ----------
            if strength == "low":
                return self._classical_deblur(input_img_path)

            # ---------- HI-DIFF ----------
            if strength == "medium":
                base_yaml = YAML_MILD
            elif strength == "high":
                base_yaml = YAML_STRONG
            else:
                base_yaml = YAML_ULTRA

            img_name = self._create_temp_dataset(input_img_path)

            temp_yaml = get_temp_subpath("config") / f"hidiff_{strength}.yml"
            self._create_temp_yaml(base_yaml, temp_yaml)

            self._run_hidiff(temp_yaml)

            blur_folder = get_temp_subpath("autoenhancement/blur")
            enhanced_output = blur_folder / img_name

            original_output = (
                HI_DIFF_ROOT
                / "results"
                / "test_HI_Diff_RealBlur_J"
                / "visualization"
                / "RealBlur_J"
                / img_name
            )

            if not original_output.exists():
                raise FileNotFoundError(f"HI-DIFF output not found: {original_output}")

            shutil.copy2(original_output, enhanced_output)

            self._log("ENGINE", f"DEBLUR finished → strength={strength}")
            return str(enhanced_output)

        finally:
            self.silent = old


# ========================================================
# CLI test
# ========================================================

if __name__ == "__main__":

    import argparse
    from utils.logger import init_logger

    parser = argparse.ArgumentParser(description="HI-Diff Deblur Executor")
    parser.add_argument("--input", required=True)
    parser.add_argument("--strength", default="medium",
                        choices=["low", "medium", "high", "ultra"])
    args = parser.parse_args()

    SESSION_ROOT = Path(__file__).resolve().parents[4] / "tuning"
    init_logger(SESSION_ROOT)

    wrapper = HiDiffWrapper()
    out = wrapper.enhance(args.input, strength=args.strength)
    LOG.info("\nOUTPUT:", out)
