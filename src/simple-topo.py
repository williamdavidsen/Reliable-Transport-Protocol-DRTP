from mininet.cli import CLI
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import Node
from mininet.topo import Topo


H1_IP = "10.0.0.1/24"
R_H1_IP = "10.0.0.2/24"
R_H2_IP = "10.0.1.1/24"
H2_IP = "10.0.1.2/24"
LINK_DELAY = "100ms"
PACKET_LOSS = None  # Example: "2%"


class LinuxRouter(Node):
    """Mininet node with IPv4 forwarding enabled."""

    def config(self, **params):
        super().config(**params)
        self.cmd("sysctl net.ipv4.ip_forward=1")

    def terminate(self):
        self.cmd("sysctl net.ipv4.ip_forward=0")
        super().terminate()


class NetworkTopo(Topo):
    def build(self, **_opts):
        h1 = self.addHost("h1", ip=None)
        router = self.addNode("r", cls=LinuxRouter, ip=None)
        h2 = self.addHost("h2", ip=None)

        self.addLink(
            h1,
            router,
            params1={"ip": H1_IP},
            params2={"ip": R_H1_IP},
        )
        self.addLink(
            router,
            h2,
            params1={"ip": R_H2_IP},
            params2={"ip": H2_IP},
        )


def configure_routes(net):
    net["h1"].cmd("ip route add 10.0.1.2 via 10.0.0.2 dev h1-eth0")
    net["h2"].cmd("ip route add 10.0.0.1 via 10.0.1.1 dev h2-eth0")
    net["h2"].cmd("ip route add 10.0.0.2 via 10.0.1.1 dev h2-eth0")


def configure_link_conditions(net):
    command = f"tc qdisc add dev r-eth1 root netem delay {LINK_DELAY}"
    if PACKET_LOSS:
        command += f" loss {PACKET_LOSS}"
    net["r"].cmd(command)


def disable_offloading(net):
    features = ("tso", "gso", "lro", "gro", "ufo")
    for host in ("h1", "h2"):
        for feature in features:
            net[host].cmd(f"ethtool -K {host}-eth0 {feature} off")


def run():
    net = Mininet(topo=NetworkTopo(), link=TCLink)
    net.start()

    configure_routes(net)
    configure_link_conditions(net)
    disable_offloading(net)

    net.pingAll()
    CLI(net)
    net.stop()


if __name__ == "__main__":
    run()
