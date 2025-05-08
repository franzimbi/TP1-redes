PASOS:
    *si queres limpiar mininet antes* sudo mn -c

    sudo mn --mac --custom ./fragmentacion_ipv4.py --topo linends,1,800 --link tc

    con perdida de paquetes 10%:
    sudo mn --mac --custom ./fragmentacion_ipv4.py --topo linends,1,800,10
<!-- --------------------------------------------------------------------------------------- -->
en mininet:
    xterm h1 h2
    s2 wireshark &   (elegir en wireshark el s2-eth0)

en la terminal h1:
    iperf3 -s

en la terminal h2:
(tcp)        iperf3 -c 10.0.0.1
(udp)        iperf3 -c 10.0.0.1 -u -l 1000 *para q el tamano de paquetes sea 1000 bytes*