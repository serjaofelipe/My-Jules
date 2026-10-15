cd homenagem-heljufel7
sed -i 's/Ashe/Olaf/g' src/App.jsx
sed -i 's/a Arqueira de Gelo/o Berserker/g' src/App.jsx
sed -i 's/Esmeralda II - 42 LP/Gold 4 - 75 LP/g' src/App.jsx
sed -i 's/54% WR/50% WR/g' src/App.jsx
sed -i 's/1,245,600 pts/8,850,970 pts/g' src/App.jsx
sed -i 's/65%/58%/g' src/App.jsx
sed -i 's/4.5:1/2.10:1/g' src/App.jsx
sed -i 's/7.8/7.4/g' src/App.jsx

# Update Match History
sed -i 's/status: "Vitória", kda: "12\/2\/8"/status: "Vitória", kda: "13\/2\/2"/g' src/App.jsx
sed -i 's/status: "Vitória", kda: "8\/1\/14"/status: "Derrota", kda: "3\/9\/7"/g' src/App.jsx
sed -i 's/status: "Derrota", kda: "4\/6\/5"/status: "Vitória", kda: "13\/2\/10"/g' src/App.jsx

# Update CSS for Olaf theme (more red/orange)
sed -i 's/14 165 233/239 68 68/g' src/index.css
sed -i 's/139, 92, 246/249, 115, 22/g' src/index.css

echo "App.jsx updated."
