# Automatic Registration

The examples show the use of `@container.wire` to mark each service. 
However, if all of them reside in packages without other objects then it is possible to automatically register 
all of them, eliminating the need for the decorator.

To achieve that you can use `container.regiter_all_in_package(yourapp.services)`

**Note:** Using this will register ALL classes found in the package.