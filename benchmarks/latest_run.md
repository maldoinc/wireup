### Wireup

```
Summary:
  Total:        2.3407 secs
  Slowest:      0.0436 secs
  Fastest:      0.0016 secs
  Average:      0.0117 secs
  Requests/sec: 4272.2336
  
  Total data:   20000 bytes
  Size/request: 2 bytes

Response time histogram:
  0.002 [1]     |
  0.006 [20]    |
  0.010 [335]   |■
  0.014 [9249]  |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.018 [244]   |■
  0.023 [29]    |
  0.027 [90]    |
  0.031 [18]    |
  0.035 [4]     |
  0.039 [4]     |
  0.044 [6]     |


Latency distribution:
  10% in 0.0104 secs
  25% in 0.0108 secs
  50% in 0.0113 secs
  75% in 0.0119 secs
  90% in 0.0129 secs
  95% in 0.0139 secs
  99% in 0.0240 secs

Details (average, fastest, slowest):
  DNS+dialup:   0.0000 secs, 0.0016 secs, 0.0436 secs
  DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0000 secs
  req write:    0.0000 secs, 0.0000 secs, 0.0011 secs
  resp wait:    0.0111 secs, 0.0016 secs, 0.0415 secs
  resp read:    0.0005 secs, 0.0000 secs, 0.0140 secs

Status code distribution:
  [200] 10000 responses
```

### FastAPI

```
Summary:
  Total:        3.6441 secs
  Slowest:      0.0469 secs
  Fastest:      0.0013 secs
  Average:      0.0182 secs
  Requests/sec: 2744.1654
  
  Total data:   20000 bytes
  Size/request: 2 bytes

Response time histogram:
  0.001 [1]     |
  0.006 [7]     |
  0.010 [11]    |
  0.015 [88]    |
  0.020 [8230]  |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.024 [1537]  |■■■■■■■
  0.029 [56]    |
  0.033 [45]    |
  0.038 [11]    |
  0.042 [7]     |
  0.047 [7]     |


Latency distribution:
  10% in 0.0163 secs
  25% in 0.0170 secs
  50% in 0.0178 secs
  75% in 0.0190 secs
  90% in 0.0202 secs
  95% in 0.0213 secs
  99% in 0.0252 secs

Details (average, fastest, slowest):
  DNS+dialup:   0.0000 secs, 0.0013 secs, 0.0469 secs
  DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0000 secs
  req write:    0.0000 secs, 0.0000 secs, 0.0007 secs
  resp wait:    0.0178 secs, 0.0012 secs, 0.0457 secs
  resp read:    0.0003 secs, 0.0000 secs, 0.0138 secs

Status code distribution:
```

### Dependency Injector

```

Summary:
  Total:        3.1758 secs
  Slowest:      0.0467 secs
  Fastest:      0.0009 secs
  Average:      0.0158 secs
  Requests/sec: 3148.7859
  
  Total data:   20000 bytes
  Size/request: 2 bytes

Response time histogram:
  0.001 [1]     |
  0.006 [6]     |
  0.010 [27]    |
  0.015 [1571]  |■■■■■■■■
  0.019 [8170]  |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.024 [148]   |■
  0.028 [49]    |
  0.033 [10]    |
  0.038 [7]     |
  0.042 [5]     |
  0.047 [6]     |


Latency distribution:
  10% in 0.0144 secs
  25% in 0.0149 secs
  50% in 0.0155 secs
  75% in 0.0164 secs
  90% in 0.0176 secs
  95% in 0.0184 secs
  99% in 0.0205 secs

Details (average, fastest, slowest):
  DNS+dialup:   0.0000 secs, 0.0009 secs, 0.0467 secs
  DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0000 secs
  req write:    0.0000 secs, 0.0000 secs, 0.0009 secs
  resp wait:    0.0155 secs, 0.0009 secs, 0.0456 secs
  resp read:    0.0003 secs, 0.0000 secs, 0.0036 secs

Status code distribution:
  [200] 10000 responses
```