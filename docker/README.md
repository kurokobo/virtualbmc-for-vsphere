# Container Examples

## Podman / Docker

You can use `podman` or `docker` to run vbmc4vsphere. Substitute commands as needed.

A [docker-compose.yml](docker-compose.yml) is also included as an example.

## Example Commands

### Build container (vsbmc:latest)
```
podman build -t vsbmc:latest .
```

### Start `vbmcd` daemon forwarding UDP ports 6240-6246 (7 virtual nodes)
```
podman run \
  -d \
  --name vsbmc \
  -v $(pwd):/vsbmc:z \
  -p "6240:6240/udp" \
  -p "6241:6241/udp" \
  -p "6242:6242/udp" \
  -p "6243:6243/udp" \
  -p "6244:6244/udp" \
  -p "6245:6245/udp" \
  -p "6246:6246/udp" \
  vsbmc
```

### Run `vbmc` commands in container
```
podman exec -it vsbmc /bin/sh

vbmc list
```

Example Output
```
+-----------+---------+---------+------+
| VM name   | Status  | Address | Port |
+-----------+---------+---------+------+
| control-0 | running | ::      | 6240 |
| control-1 | running | ::      | 6241 |
| control-2 | running | ::      | 6242 |
| worker-0  | running | ::      | 6250 |
| worker-1  | running | ::      | 6251 |
| worker-2  | running | ::      | 6252 |
| worker-3  | running | ::      | 6253 |
+-----------+---------+---------+------+
```
