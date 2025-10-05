# Claude Code 编码规范

## 项目概述
电梯调度模型，我们需要在client_examples文件夹下编写算法，调度电梯正确接送客人。现在有如下简化：
1. 我们知道所有乘客上下电梯的目的楼层
2. 乘客不会放弃等待
3. 乘客不会在电梯内改变目的地
4. 乘客上下电梯按先来后到顺序
5. 乘客不会通过多次上下电梯实现目的地的到达
类型参数和接口说明elevator_saga/client/proxy_models.py、elevator_saga/core/models.py
https://zgca-forge.github.io/Elevator/client.html


### 设计模式
遵循最简化要求，注释要详细，代码要尽量简化。

## 当前进度
可随时查看git历史记录。当前已经开发了一个简易的例子，在elevator_saga\client_examples\simple_example.py中。
