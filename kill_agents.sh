#!/bin/bash

# Script para matar todos os processos do agente

echo "🔍 Processos encontrados:"
ps aux | grep -E "(autonomous_agent_demo|python.*agent|claude.*--output-format)" | grep -v grep

echo ""
echo "💀 Matando processos..."

# Matar processos do Python agent
pkill -f "autonomous_agent_demo"

# Matar processos do Claude SDK
pkill -f "claude.*--output-format"

# Matar processos específicos por PID (backup)
kill -9 16124 2>/dev/null
kill -9 97426 2>/dev/null
kill -9 94731 2>/dev/null

echo ""
echo "🧹 Limpando arquivos de lock..."

# Remover locks do projeto principal
find /Users/adrianoboldarini/7clicks/autocoder-tauri -name ".agent.lock" -delete 2>/dev/null
find /Users/adrianoboldarini/lalala -name ".agent.lock" -delete 2>/dev/null

echo ""
echo "✅ Verificando se ainda há processos:"
ps aux | grep -E "(autonomous_agent_demo|python.*agent|claude.*--output-format)" | grep -v grep || echo "Nenhum processo encontrado ✓"

echo ""
echo "🎉 Pronto! Tente iniciar o agente novamente."
