#!/bin/bash
# ObserveCo terminal demo — record with: bash demo.sh
# Or pipe to terminalizer/asciinema for GIF

echo "# ObserveCo — Runtime Observability for AI Agents"
echo "# ─────────────────────────────────────────────────"
sleep 1
echo ""
echo "$ pip install observeco[dashboard]"
sleep 0.5
echo "Collecting observeco..."
echo "Installing collected packages: observeco"
echo "Successfully installed observeco-0.1.0"
sleep 1
echo ""
echo "$ observeco --version"
echo "observeco v0.1.0"
sleep 0.5
echo ""
echo "$ observeco pulse check"
echo "╔══════════════════════════════════════════════╗"
echo "║  Agent       Status     Last Check           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  hermes      ● Healthy  Just now             ║"
echo "║  kepler      ● Healthy  12s ago              ║"
echo "║  hound       ● Healthy  24s ago              ║"
echo "║  dreamer     ● Healthy  6s ago               ║"
echo "║  pa          ● Healthy  18s ago              ║"
echo "╚══════════════════════════════════════════════╝"
sleep 1
echo ""
echo "$ echo "Your system prompt" | observeco chisel trim"
echo "Token breakdown:"
echo "  Identity    320 tok  ████████████  22%"
echo "  Skills      480 tok  ██████████████████  33%"
echo "  Memory      210 tok  ████████  14%"
echo "  Tools       150 tok  ██████  10%"
echo "  Guidance    300 tok  ███████████  21%"
echo "  ───────────────────────────────────────────"
echo "  Total     1,460 tok  █████████████████████████"
sleep 1
echo ""
echo "$ observeco clawforge garden --agent kepler"
echo "Memory garden scan for 'kepler':"
echo "  ✅ 32 entries checked"
echo "  ⚠️  2 duplicates found  (managed-memory)"
echo "  ⚠️  3 contradictions    (agent_name, role)"
echo "  ✅ 0 stale entries"
echo ""
echo "  Run 'clawforge garden --agent kepler --fix' to resolve."
sleep 1
echo ""
echo "$ observeco dashboard"
echo "  Dashboard running at http://localhost:9122"
echo "  Open your browser to see the fleet view."
echo ""
echo "# That's the ObserveCo experience."
echo "# pip install, 60 seconds, zero config."
