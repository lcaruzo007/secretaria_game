# Estrutura de Mapas

## Configuração dos Mapas

Cada mapa precisa de dois arquivos:

### 1. Arquivo JSON (colisões)
- **Localização**: `assets/mapas/mapa_01.json`
- **Contém**: Dados de colisão, objetos e metadata do mapa
- **Gerado por**: RPG Map 2 (Deepnight)

### 2. Arquivo PNG (visual)
- **Localização**: `assets/images/backgrounds/mapas/mapa_01.png`
- **Contém**: Imagem visual renderizada do mapa com todos os detalhes
- **Gerado por**: Exportar como PNG do RPG Map 2 (File → Export as PNG)

## Como Adicionar um Novo Mapa

1. No RPG Map 2, abra/crie seu mapa
2. Salve como `mapa_XX.json` em `assets/mapas/`
3. Exporte como PNG: `File → Export as PNG`
4. Salve o PNG como `mapa_XX.png` em `assets/images/backgrounds/mapas/`
5. No `game.py`, atualize o `mapa_data = _load_map_data()` para carregar o novo arquivo

## Sistema de Colisão

O JSON contém um array `collisions` no formato `"index:tipo"`:
- `tipo = 1`: Parede/obstáculo (bloqueia personagem)
- `tipo = 2`: Passagem/porta (não bloqueia - permite passar)

O jogo converte automaticamente as coordenadas de tiles para pixels usando as dimensões do mapa (`w`, `h`).
