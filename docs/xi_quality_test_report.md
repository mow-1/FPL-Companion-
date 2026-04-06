# XI Quality Test Report

User: testuser  |  Gameweek: Gameweek 30

## Layer 1 — Availability Filter
No players filtered -- all have chance_of_playing >= 30%

## Layer 2 — Fixture Weighting
Fixture weighting did not change the XI composition

FDR adjustments in new XI:
  Raya                 FDR=3 -  raw=3.8 → adj=3.8
  Lacroix              FDR=3 -  raw=3.2 → adj=3.2
  Guéhi                FDR=4 v  raw=3.4 → adj=3.1
  Semenyo              FDR=4 v  raw=5.7 → adj=5.1
  Gravenberch          FDR=3 -  raw=3.1 → adj=3.1
  Mbeumo               FDR=3 -  raw=3.2 → adj=3.2
  João Pedro           FDR=3 -  raw=4.9 → adj=4.9
  Haaland              FDR=4 v  raw=5.8 → adj=5.2
  Ekitiké              FDR=3 -  raw=2.8 → adj=2.8
  Anthony              FDR=3 -  raw=2.7 → adj=2.7
  Gabriel              FDR=3 -  raw=4.1 → adj=4.1

## Layer 3 — Dream Team Captain Bonus
Captain CHANGED: Haaland → Semenyo (dream team bonus influenced selection)
  Raya                 ⭐×1 dream team apps, captain×0
  Lacroix              ⭐×2 dream team apps, captain×0
  Guéhi                ⭐×3 dream team apps, captain×1
  Semenyo              ⭐×4 dream team apps, captain×1
  Gravenberch          ⭐×3 dream team apps, captain×0
  Mbeumo               ⭐×1 dream team apps, captain×0
  João Pedro           ⭐×5 dream team apps, captain×1
  Haaland              ⭐×9 dream team apps, captain×0
  Ekitiké              ⭐×4 dream team apps, captain×0
  Anthony              ⭐×2 dream team apps, captain×0
  Gabriel              ⭐×5 dream team apps, captain×0

## Layer 4 — Groq Reasoning
Approved: True
Team Rating: strong
Captain Reasoning: Semenyo is the correct captain choice given his impressive form and Manchester City's home advantage, despite a tougher fixture, his potential for high returns makes him a compelling pick.
No swaps suggested — optimizer XI confirmed
Overall Comment: The proposed XI looks well-balanced, with a good mix of defensive and attacking potential, and the captain choice is justified given Semenyo's form and fixture, making it a strong team for Gameweek 31.

## Side-by-Side XI Comparison
Player                 OLD XI   NEW XI   FDR  Adj Pts 
--------------------------------------------------------
  Raya                 ✓        ✓           3      3.8
  Lacroix              ✓        ✓           3      3.2
  Guéhi                ✓        ✓           4      3.1
  Semenyo              ✓        ✓           4      5.1
  Gravenberch          ✓        ✓           3      3.1
  Mbeumo               ✓        ✓           3      3.2
  João Pedro           ✓        ✓           3      4.9
  Haaland              ✓        ✓           4      5.2
  Ekitiké              ✓        ✓           3      2.8
  Anthony              ✓        ✓           3      2.7
  Gabriel              ✓        ✓           3      4.1

## Overall Verdict
Impact summary: Layer 3 changed captain from Haaland to Semenyo