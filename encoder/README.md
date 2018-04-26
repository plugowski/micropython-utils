# Simple Usage

```python
from encoder import Encoder
e = Encoder(14, 12)

while True:
    print(e.position)
```

You can also define callback function which will be triggered for each encoder move:

```python
from encoder import Encoder

def showvalue(value):
    print(value)
    
e = Encoder(14, 12, showvalue)
```

By default encoder counts (increment/decrement) steps to infinity, but you can set range by setting `min` and `max` 
parameters in constructor.

```python
Encoder(14, 12, showvalue, min=0, max=100)
``` 

By setting `step` parameter, one step of encoder increase value by that value.