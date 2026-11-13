# Vérification des horodatages et des plages d’attaque

- Lignes de sortie : 2827677
- Échecs de parsing Timestamp : 0
- Écarts entre date parsée et day : 0
- Échantillon de développement : 5000 flux (graine `seeds.global`)

## Parsing par fichier

| Fichier | Jour | Lignes | Échecs de parsing |
|---|---|---:|---:|
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Friday | 225709 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Friday | 286095 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Friday | 190909 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Monday | 529450 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Thursday | 288253 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Thursday | 170230 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Tuesday | 445641 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Wednesday | 691390 | 0 |

## Résumé par jour

| Jour | Flux | ts_end min (epoch s) | ts_end max (epoch s) | Étendue max-min (s) | Somme Flow Duration (s) | Durées ≤ 0 |
|---|---:|---:|---:|---:|---:|---:|
| Monday | 529450 | 1499043601.000003 | 1499086907.827160 | 43306.827157 | 5505461.794430 | 15 |
| Tuesday | 445641 | 1499158440.000001 | 1499187620.683396 | 29180.683395 | 4806648.791426 | 17 |
| Wednesday | 691390 | 1499244120.000003 | 1499274600.003557 | 30480.003554 | 19396848.258315 | 21 |
| Thursday | 458483 | 1499331540.000269 | 1499360664.760928 | 29124.760659 | 4713407.716228 | 15 |
| Friday | 702713 | 1499418000.000002 | 1499446956.941088 | 28956.941086 | 7432048.107939 | 47 |

## Vérification des plages d’attaque

- Tolérance configurée : ±2 minute(s).

| Jour | Classe | Plage(s) | Flux de la classe ce jour | Dans la plage | % dans la plage | Hors plage |
|---|---|---|---:|---:|---:|---:|
| Monday | FTP-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | SSH-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | DoS slowloris | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | DoS Slowhttptest | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | DoS Hulk | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | DoS GoldenEye | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Heartbleed | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Web Attack - Brute Force | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Web Attack - XSS | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Web Attack - Sql Injection | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Infiltration | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | Bot | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | PortScan | aucune plage définie | 0 | n/a | n/a | n/a |
| Monday | DDoS | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | FTP-Patator | 09:20–10:20 | 7935 | 7933 | 99.97% | 2 |
| Tuesday | SSH-Patator | 14:00–15:00 | 5897 | 5158 | 87.47% | 739 |
| Tuesday | DoS slowloris | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | DoS Slowhttptest | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | DoS Hulk | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | DoS GoldenEye | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Heartbleed | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Web Attack - Brute Force | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Web Attack - XSS | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Web Attack - Sql Injection | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Infiltration | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | Bot | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | PortScan | aucune plage définie | 0 | n/a | n/a | n/a |
| Tuesday | DDoS | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | FTP-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | SSH-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | DoS slowloris | 09:47–10:10 | 5796 | 5790 | 99.90% | 6 |
| Wednesday | DoS Slowhttptest | 10:14–10:35 | 5499 | 5499 | 100.00% | 0 |
| Wednesday | DoS Hulk | 10:43–11:00 | 230123 | 229978 | 99.94% | 145 |
| Wednesday | DoS GoldenEye | 11:10–11:23 | 10293 | 10293 | 100.00% | 0 |
| Wednesday | Heartbleed | 15:12–15:32 | 11 | 11 | 100.00% | 0 |
| Wednesday | Web Attack - Brute Force | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | Web Attack - XSS | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | Web Attack - Sql Injection | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | Infiltration | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | Bot | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | PortScan | aucune plage définie | 0 | n/a | n/a | n/a |
| Wednesday | DDoS | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | FTP-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | SSH-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | DoS slowloris | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | DoS Slowhttptest | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | DoS Hulk | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | DoS GoldenEye | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | Heartbleed | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | Web Attack - Brute Force | 09:20–10:00 | 1507 | 1502 | 99.67% | 5 |
| Thursday | Web Attack - XSS | 10:15–10:35 | 652 | 652 | 100.00% | 0 |
| Thursday | Web Attack - Sql Injection | 10:40–10:42 | 21 | 21 | 100.00% | 0 |
| Thursday | Infiltration | 14:19–15:45 | 36 | 36 | 100.00% | 0 |
| Thursday | Bot | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | PortScan | aucune plage définie | 0 | n/a | n/a | n/a |
| Thursday | DDoS | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | FTP-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | SSH-Patator | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | DoS slowloris | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | DoS Slowhttptest | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | DoS Hulk | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | DoS GoldenEye | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Heartbleed | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Web Attack - Brute Force | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Web Attack - XSS | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Web Attack - Sql Injection | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Infiltration | aucune plage définie | 0 | n/a | n/a | n/a |
| Friday | Bot | 10:02–11:02 | 1956 | 1471 | 75.20% | 485 |
| Friday | PortScan | 13:55–15:29 | 158804 | 158796 | 99.99% | 8 |
| Friday | DDoS | 15:56–16:16 | 128025 | 128025 | 100.00% | 0 |

### Classes absentes ou hors configuration

- Classes configurées absentes des données : aucune.
- Classes des données absentes de la configuration : BENIGN. Les labels ne sont pas modifiés.

## Limites

- 7 fichier(s) sur 8 n’ont pas de secondes dans le format source (résolution d’une minute).
- Flux dont la seconde de l’heure de début corrigée vaut 0 : Monday 7693/529450 (1.45 %), autres jours 2298227/2298227 (100.00 %).
- Fichiers d’origine dont les heures de début ne sont pas triées : Monday-WorkingHours.pcap_ISCX.csv (208741 inversion(s)); Tuesday-WorkingHours.pcap_ISCX.csv (159376 inversion(s)); Wednesday-workingHours.pcap_ISCX.csv (163845 inversion(s)).
- Durée maximale observée : 120.000000 seconde(s) (120000000 microsecondes).
- Les labels d’origine sont conservés ; les écarts aux fenêtres ne sont pas corrigés.
