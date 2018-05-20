1 => mininet/wifi/net.py의 Mininet_wifi class 생성자에서 +max_sector, sector, side_dB, main_dB 

sector는 현재 sector의 상태. 기점은 임의로 왼쪽 맨위부터 시작합니다.
            
    0       |      1
--------------------
    3       |      2     
            
ex) max_sector가 4라면 sector가 4등분되어 있는 상태로, sector 값에 따라 범위가 달라지며 
현재 sector가 0이라면 sector 0의 범위에는 main_dB(=-20)을 적용, 나머지에는 side_dB(=-5)을 적용 

2 => mininet/wifi/net.py의 addAccessPoint, addStation에서 max_sector, sector, side_dB, main_dB 추가


* mininet py에서 topology 생성시 link=wmediumd와 mode를 설정해주면 wmediumd가 작동하도록 되어있음.

mininet station parameter -> wserver_messages.c에서 전달 , 내부에서 계산한 error_prob -> wserevr_messages_network.c에서 답장

python mininet process에서 error_prob를 보고 통신 판단


3 => mininet/wifi/wmediumdConnector.py에서 서버 메세지(max_sector, sector, main_dB, side_dB) 타입 추가

4 => mininet/wifi/node.py에서 SetParameter 등 추가

5 => wmediumd sta structure에서 Parameter 추가

6 => wmediumd Server에서 Parameter 전달 및 대입 추가

7 => Parameter를 토대로 Angle, Path loss 계산 추가

8 => wmediumd Server에서 WmediumdConnector로 error_prob_matrix를 되돌려줌
