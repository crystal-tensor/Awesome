import argparse
import json
from pathlib import Path

import pandas as pd

from pt_data_transformer import export_model_ohlcv, transform_ohlcv_with_pt_model


def load_params(args) -> dict:
    if args.model_json:
        with open(args.model_json, encoding="utf-8") as file:
            payload = json.load(file)
        model = payload.get("deliverableModel", payload)
        if args.market and args.market in model.get("marketParameters", {}):
            return model["marketParameters"][args.market]
        return model["globalParameters"]
    return {"mode": args.mode, "qHead": args.q_head, "qTail": args.q_tail, "eta": args.eta}


def main() -> None:
    parser = argparse.ArgumentParser(description="把机构原始 OHLCV CSV 转换为 PT 模型 OHLCV CSV")
    parser.add_argument("--input", required=True, help="原始 CSV，包含 date/open/high/low/close/volume")
    parser.add_argument("--output", required=True, help="输出 CSV")
    parser.add_argument("--model-json", default="", help="训练输出 JSON，可直接读取 deliverableModel")
    parser.add_argument("--market", default="", help="使用模型 JSON 中的指定市场参数")
    parser.add_argument("--q-head", type=float, default=0.8)
    parser.add_argument("--q-tail", type=float, default=0.95)
    parser.add_argument("--eta", type=float, default=0.5)
    parser.add_argument("--mode", default="tail_denoise")
    parser.add_argument("--full-output", action="store_true", help="输出包含原始列、bucket、pt_weight 等完整诊断字段")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

    params = load_params(args)
    transformed = transform_ohlcv_with_pt_model(
        df,
        q_head=float(params["qHead"]),
        q_tail=float(params["qTail"]),
        eta=float(params["eta"]),
        mode=str(params.get("mode", "tail_denoise")),
    )

    output_df = transformed if args.full_output else export_model_ohlcv(transformed)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    output_df.reset_index().to_csv(args.output, index=False)
    print(
        json.dumps(
            {
                "input": args.input,
                "output": args.output,
                "rows": int(len(output_df)),
                "params": {
                    "mode": params.get("mode", "tail_denoise"),
                    "qHead": params["qHead"],
                    "qTail": params["qTail"],
                    "eta": params["eta"],
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
