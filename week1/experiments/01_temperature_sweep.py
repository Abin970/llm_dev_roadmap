"""
Experiment 1 -- Temperature sweep
==================================
Hypothesis : raising temperature increases variance across otherwise-identical
             calls; temperature=0 is close to, but not guaranteed to be,
             perfectly deterministic.
Setup      : one fixed prompt, 3 temperatures, 3 runs each -- 9 calls total.
Teaches    : sampling is a design choice with a real, visible effect, not a
             knob you turn to "fix" bad output.

Run: python experiments/01_temperature_sweep.py   (from the week1/ directory)
"""
import _bootstrap  # noqa: F401  (adds week1/ to sys.path -- see _bootstrap.py)
from llm_client import chat

# TODO: swap this for a prompt in your own domain if you like -- open-ended
# enough that wording can plausibly vary (a naming/brainstorming task works
# well; a factual lookup won't show much variance at any temperature).
PROMPT = "Suggest a business idea for homemade products that could be sold online."

TEMPERATURES = [0.0, 0.7, 1.3]
RUNS_PER_TEMPERATURE = 3
TEMP_SWEEP_MODEL = "gpt-4.1-nano"

def main() -> None:
    messages = [{"role": "developer", "content": "Answer in one short line."}, {"role": "user", "content": PROMPT}]
    for temp in TEMPERATURES:
        print(f"\n=== temperature={temp} ===")
        for i in range(RUNS_PER_TEMPERATURE):
            # TODO: call chat(messages, temperature=temp) and print(f"  {i+1}: {result}")
            chat_result = chat(model=TEMP_SWEEP_MODEL, messages=messages, temperature=temp)
            print(f"  {i+1}: {chat_result}")


if __name__ == "__main__":
    main()

# --- OBSERVATIONS (fill in after running) ----------------------------------
# temperature=0.0 -- identical across all 3 runs? if not, how did they differ?
#
# === temperature=0.0 ===
#  1: Create personalized handmade candles with unique scents and designs for online sale.
#  2: Create personalized handmade candles with unique scents and designs for online sale.
#  3: Create personalized handmade candles with unique scents and customizable labels for online sale.

# 
# temperature=0.7 -- how much did wording vary? was the *substance* stable?
#   
# === temperature=0.7 ===
#  1: Create handmade personalized jewelry and accessories sold through an online store.
#  2: Create personalized handmade candles and home decor items for online sale.
#  3: Create personalized homemade candles with unique scents and customizable labels for online sale.
# 
# temperature=1.3 -- at what point did quality/coherence start to degrade?
#   
# === temperature=1.3 ===
#  1: Create customized handmade candles with personalized scents and designs for online sale.
#  2: Create personalized handmade skincare and wellness products with natural ingredients tailored to customer preferences.
#  3: Create customized handcrafted candles or bath bombs with unique scents and packaging for online sales.
#
# One sentence: when would you actually want temperature=0 in a real app,
# and when would that be the wrong choice?
#
# we can clearly see the incresing variance in the outputs as the temperature increases.
# At temperature=0, the outputs are mostly identical, which is useful for tasks 
# requiring consistency and reliability. However, at higher temperatures,
#  the outputs become more diverse and creative, which can be beneficial for 
# brainstorming or generating novel ideas. Therefore,temperature=0 is ideal
# for deterministic tasks, while higher temperatures are better suited for creative exploration.
