# dnsplit

DNSplit will split your DNS traffic by dispatching queries to specific nameservers according to rules and conditions.

### yesbutwhy

I have been using [Unbound](https://unbound.net/) and it's great, but it didn't totally meet what I needed. Dnsplit lacks most of the features of Unbound, but here is what it can be used for:

- Forward DNS queries for specific DNS suffixes to the relevant nameservers
- Make decisions according to rules with conditions, such as:
    - Forward queries for lists of pre-configured domains to specific nameservers
    - If you are connected to a VPN (e.g. interface tun0 is up), forward queries for internal domains to internal nameservers
    - If your network interface has an address in a particular network, forward queries to the corresponding nameservers
    - For all of the above, optionally add domain wildcard filters for the rules to match.
    - If no previous rule was matched, forward queries to the default (public) nameservers
    - And more (See examples)

### Examples

Most of the examples below are from the sample configuration file

Rules can be created to forward requests to certain dns servers according to specific conditions. The rules are processed sequentially, meaning that when a rule is matched the corresponding nameservers will be used and no more rules will be processed.

Conditions can be:
- an interface is up and has link (e.g. "tun0 up")
- an interface exists but is down (e.g. "tun0 down")
- an interface is in a specific network (e.g. "eth0 192.168.0.0/24")

The "match" parameter can be used to forward queries for specific domains to the internal nameservers and all other queries to the default nameservers as configured above.

For example, you may want to forward requests for your company's dns suffix only when you are connected to VPN and otherwise to the default nameservers. In this case, you need to specify that those requests will be forwarded to internal nameservers only if the VPN interface is up and has link. Such a rule would look like:

```
   {
       "name": "My Company's Split-Tunnel VPN",
       "match": "*.mycompany.*",
       "condition": "tun0 up",
       "nameservers": ["10.0.0.10", "10.0.0.20"]
   },
```

An other example would be if you want to use the internal nameservers from a physical LAN that you connect to. You can specify that an interface needs to have an IP address in a particular network to apply the rule:

```
   {
       "name": "Corporate LAN",
       "match": "*.internaldomain.net",
       "condition": "eth0 192.168.42.0/23",
       "nameservers": ["192.168.42.100", "192.168.42.101"]
   },
```

The "match" parameter can also be omitted to match all queries. A rule to use exclusively the internal nameservers when connected to the LAN would look like this:

```
   {
       "name": "Corporate LAN",
       "condition": "eth0 192.168.42.0/23",
       "nameservers": ["192.168.42.100", "192.168.42.101"]
   },
```
The "condition" parameter can also be omitted to function in traditional dns-relay mode.  However, "match" and "condition" can not be both omitted in the same rule as this would overwrite the default nameservers.

The "match" parameter can also be a list for multiple matches. Example rule: use google nameservers for all google queries:

```
   {
     "name": "Use Google DNS for all Google queries",
     "match": ["google.com", "*.google.*", "*.gstatic.com", "*.gmail.com"],
     "nameservers": ["8.8.8.8", "8.8.4.4"]
    }
```

### More examples

If you want to use your company's nameservers when connected to the corporate LAN but don't want to let them know that you are slacking off on facebook instead of working. Create 2 rules as below.

```
   {
       "name": "When at work forward FB queries to OpenDNS",
        "match": ["facebook.com", "*.facebook.com", "*.fbcdn.net"],
       "condition": "eth0 172.16.21.0/20",
       "nameservers": ["208.67.222.222", "208.67.220.220"]
   },
   {
       "name": "When at work forward everything else to internal NS",
       "condition": "eth0 172.16.21.0/20",
       "nameservers": ["172.16.21.110", "172.16.21.110]
   },
```

You can also use "interface down" as a condition. This may be useful if you want to use specific nameservers only if you are disconnected from the VPN. Example:

```
   {
       "name": "When off VPN, send queries for mycompany to other NS",
        "match": ["mycompany.com", "*.mycompany.com"],
       "condition": "tun0 down",
       "nameservers": ["37.235.1.174", "37.235.1.177"]
   }
```

### Installation

dnsplit require some python libraries. To install them, run:

```
sudo pip install -r requirements.txt
```

First, copy the configuration file to `/etc`:

```
sudo cp dnsplit.conf /etc
```

Edit the file to create the rules you want and set additional parameters as you need.

You can simply run `sudo python dnsplit.py` from the command line to try it out. If you want to install it on the system, the script comes with a unit file for `systemd`. Suppose you want to install dnsplit in `/usr/local/bin`, proceed as follows:

```
sudo cp dnsplit.py /usr/local/bin
sudo cp dnsplit.service /etc/systemd/system/multi-user.target.wants
```

Then, enable the service, reload the daemon, and start the service:

```
sudo systemctl enable /etc/systemd/system/multi-user.target.wants/dnsplit.service
sudo systemctl daemon-reload
sudo systemctl start dnsplit
```

Lastly, update your `resolv.conf` file:

```
sudo cp /etc/resolv.conf /etc/resolv.conf.backup
sudo echo nameserver 127.0.0.1 > /etc/resolv.conf
sudo chattr +i /etc/resolv.conf
```

That's all.
