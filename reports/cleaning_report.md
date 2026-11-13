# Rapport de nettoyage CIC-IDS2017

- Fichiers traités : 8
- Fichier Parquet : `data\interim\clean_raw.parquet`
- Nombre final de lignes : 2827677
- Nombre final de features : 69

## Lignes par fichier et par étape

| Fichier | Jour | Lues | Après étape 1 | Après étape 2 | Après étape 3 | Après étape 4 | Après étape 5 | Après étape 6 | Après étape 7 | Après étape 8 | Après étape 9 | Après étape 10 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Friday | 225745 | 225745 | 225745 | 225745 | 225745 | 225711 | 225709 | 225709 | 225709 | 225709 | 225709 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Friday | 286467 | 286467 | 286467 | 286467 | 286467 | 286096 | 286095 | 286095 | 286095 | 286095 | 286095 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Friday | 191033 | 191033 | 191033 | 191033 | 191033 | 190911 | 190909 | 190909 | 190909 | 190909 | 190909 |
| Monday-WorkingHours.pcap_ISCX.csv | Monday | 529918 | 529918 | 529918 | 529918 | 529918 | 529481 | 529450 | 529450 | 529450 | 529450 | 529450 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Thursday | 288602 | 288602 | 288602 | 288602 | 288602 | 288395 | 288253 | 288253 | 288253 | 288253 | 288253 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Thursday | 458968 | 458968 | 458968 | 458968 | 170366 | 170231 | 170230 | 170230 | 170230 | 170230 | 170230 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Tuesday | 445909 | 445909 | 445909 | 445909 | 445909 | 445645 | 445641 | 445641 | 445641 | 445641 | 445641 |
| Wednesday-workingHours.pcap_ISCX.csv | Wednesday | 692703 | 692703 | 692703 | 692703 | 692703 | 691406 | 691390 | 691390 | 691390 | 691390 | 691390 |

## Causes de suppression de lignes

| Fichier | Lignes vides | Sans Timestamp | Avec inf/-inf dans les features | Avec NaN dans les features seulement | Lignes supprimées à l’étape 5 | Doublons supprimés |
|---|---:|---:|---:|---:|---:|---:|
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | 0 | 0 | 34 | 0 | 34 | 2 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | 0 | 0 | 371 | 0 | 371 | 1 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | 0 | 0 | 122 | 0 | 122 | 2 |
| Monday-WorkingHours.pcap_ISCX.csv | 0 | 0 | 437 | 0 | 437 | 31 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | 0 | 0 | 207 | 0 | 207 | 142 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | 288602 | 0 | 135 | 0 | 135 | 1 |
| Tuesday-WorkingHours.pcap_ISCX.csv | 0 | 0 | 264 | 0 | 264 | 4 |
| Wednesday-workingHours.pcap_ISCX.csv | 0 | 0 | 1297 | 0 | 1297 | 16 |

## Cellules NaN et infini par feature

| Fichier | Feature | NaN | inf/-inf remplacés par NaN |
|---|---|---:|---:|
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Active Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Active Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Active Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow Bytes/s | 4 | 30 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Flow Packets/s | 0 | 34 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Protocol | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Active Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Active Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Active Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow Bytes/s | 15 | 356 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Flow Packets/s | 0 | 371 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Protocol | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Active Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Active Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Active Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow Bytes/s | 28 | 94 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Flow Packets/s | 0 | 122 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Protocol | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Friday-WorkingHours-Morning.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Active Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Active Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Active Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow Bytes/s | 64 | 373 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Flow Packets/s | 0 | 437 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Protocol | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Monday-WorkingHours.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Active Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Active Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Active Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow Bytes/s | 18 | 189 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Flow Packets/s | 0 | 207 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Protocol | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Active Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Active Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Active Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow Bytes/s | 20 | 115 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Flow Packets/s | 0 | 135 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Protocol | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Active Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Active Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Active Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow Bytes/s | 201 | 63 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Flow Packets/s | 0 | 264 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Protocol | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Tuesday-WorkingHours.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | ACK Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Active Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Active Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Active Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Active Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Average Packet Size | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Avg Bwd Segment Size | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Avg Fwd Segment Size | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Avg Bulk Rate | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Avg Bytes/Bulk | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Avg Packets/Bulk | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Header Length | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd IAT Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd IAT Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd IAT Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd IAT Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd IAT Total | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd PSH Flags | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Packet Length Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Packet Length Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Packet Length Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Packet Length Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd Packets/s | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Bwd URG Flags | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | CWE Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Down/Up Ratio | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | ECE Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | FIN Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow Bytes/s | 1008 | 289 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow Duration | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow IAT Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow IAT Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow IAT Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow IAT Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Flow Packets/s | 0 | 1297 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Avg Bulk Rate | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Avg Bytes/Bulk | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Avg Packets/Bulk | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Header Length | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd IAT Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd IAT Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd IAT Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd IAT Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd IAT Total | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd PSH Flags | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Packet Length Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Packet Length Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Packet Length Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Packet Length Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd Packets/s | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Fwd URG Flags | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Idle Max | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Idle Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Idle Min | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Idle Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Init_Win_bytes_backward | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Init_Win_bytes_forward | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Max Packet Length | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Min Packet Length | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | PSH Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Packet Length Mean | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Packet Length Std | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Packet Length Variance | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Protocol | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | RST Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | SYN Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Subflow Bwd Bytes | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Subflow Bwd Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Subflow Fwd Bytes | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Subflow Fwd Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Total Backward Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Total Fwd Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Total Length of Bwd Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | Total Length of Fwd Packets | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | URG Flag Count | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | act_data_pkt_fwd | 0 | 0 |
| Wednesday-workingHours.pcap_ISCX.csv | min_seg_size_forward | 0 | 0 |

## Doublons supprimés par jour et par classe

| Jour | Classe | Doublons supprimés |
|---|---|---:|
| Friday | BENIGN | 5 |
| Monday | BENIGN | 31 |
| Thursday | BENIGN | 143 |
| Tuesday | BENIGN | 4 |
| Wednesday | BENIGN | 15 |
| Wednesday | DoS Hulk | 1 |

## Classes avant et après nettoyage

| Classe | Avant étape 4 (lignes non vides, labels nettoyés) | Après étape 10 |
|---|---:|---:|
| BENIGN | 2273097 | 2271122 |
| Bot | 1966 | 1956 |
| DDoS | 128027 | 128025 |
| DoS GoldenEye | 10293 | 10293 |
| DoS Hulk | 231073 | 230123 |
| DoS Slowhttptest | 5499 | 5499 |
| DoS slowloris | 5796 | 5796 |
| FTP-Patator | 7938 | 7935 |
| Heartbleed | 11 | 11 |
| Infiltration | 36 | 36 |
| PortScan | 158930 | 158804 |
| SSH-Patator | 5897 | 5897 |
| Web Attack - Brute Force | 1507 | 1507 |
| Web Attack - Sql Injection | 21 | 21 |
| Web Attack - XSS | 652 | 652 |

Aucune classe présente avant nettoyage n’a été perdue.

## Colonnes supprimées

- `Bwd Avg Bulk Rate`
- `Bwd Avg Bytes/Bulk`
- `Bwd Avg Packets/Bulk`
- `Bwd PSH Flags`
- `Bwd URG Flags`
- `Fwd Avg Bulk Rate`
- `Fwd Avg Bytes/Bulk`
- `Fwd Avg Packets/Bulk`
- `Fwd Header Length.1`

## Features conservées

- `Protocol`
- `Flow Duration`
- `Total Fwd Packets`
- `Total Backward Packets`
- `Total Length of Fwd Packets`
- `Total Length of Bwd Packets`
- `Fwd Packet Length Max`
- `Fwd Packet Length Min`
- `Fwd Packet Length Mean`
- `Fwd Packet Length Std`
- `Bwd Packet Length Max`
- `Bwd Packet Length Min`
- `Bwd Packet Length Mean`
- `Bwd Packet Length Std`
- `Flow Bytes/s`
- `Flow Packets/s`
- `Flow IAT Mean`
- `Flow IAT Std`
- `Flow IAT Max`
- `Flow IAT Min`
- `Fwd IAT Total`
- `Fwd IAT Mean`
- `Fwd IAT Std`
- `Fwd IAT Max`
- `Fwd IAT Min`
- `Bwd IAT Total`
- `Bwd IAT Mean`
- `Bwd IAT Std`
- `Bwd IAT Max`
- `Bwd IAT Min`
- `Fwd PSH Flags`
- `Fwd URG Flags`
- `Fwd Header Length`
- `Bwd Header Length`
- `Fwd Packets/s`
- `Bwd Packets/s`
- `Min Packet Length`
- `Max Packet Length`
- `Packet Length Mean`
- `Packet Length Std`
- `Packet Length Variance`
- `FIN Flag Count`
- `SYN Flag Count`
- `RST Flag Count`
- `PSH Flag Count`
- `ACK Flag Count`
- `URG Flag Count`
- `CWE Flag Count`
- `ECE Flag Count`
- `Down/Up Ratio`
- `Average Packet Size`
- `Avg Fwd Segment Size`
- `Avg Bwd Segment Size`
- `Subflow Fwd Packets`
- `Subflow Fwd Bytes`
- `Subflow Bwd Packets`
- `Subflow Bwd Bytes`
- `Init_Win_bytes_forward`
- `Init_Win_bytes_backward`
- `act_data_pkt_fwd`
- `min_seg_size_forward`
- `Active Mean`
- `Active Std`
- `Active Max`
- `Active Min`
- `Idle Mean`
- `Idle Std`
- `Idle Max`
- `Idle Min`
