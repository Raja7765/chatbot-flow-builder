import json

with open(r'C:\Users\rajas\.gemini\antigravity\brain\6a122966-fed9-49e8-96e8-591cee602b79\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if "report it before making" in line:
            data = json.loads(line)
            print(f"Step {idx}: source={data.get('source')}, type={data.get('type')}")
            # print snippet
            content = data.get('content', '')
            for l in content.split('\n')[:15]:
                print("  ", l)

