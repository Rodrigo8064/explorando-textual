#!/bin/bash

echo "================================"
echo " Script iniciado"
echo "================================"

echo

echo "Usuário: $(whoami)"
echo "Diretório: $(pwd)"

echo
echo "Testando sudo..."

sudo -v

echo
echo "sudo funcionou!"

echo
echo "Executando comando privilegiado..."

sudo touch /tmp/tui-terminal-test

echo
echo "Arquivo criado em /tmp/tui-terminal-test"

echo
echo "================================"
echo " Script finalizado"
echo "================================"
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
echo
read -p "Pressione ENTER para sair..."
