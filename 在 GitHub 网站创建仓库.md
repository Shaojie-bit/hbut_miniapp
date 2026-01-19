您必须先告诉 Git 您的名字和邮箱，这样它才知道是谁提交了代码。

在您的 Git Bash 终端中输入以下两条命令：

Bash

```
git config --global user.name "Shaojie-bit"
```

Bash

```
git config --global user.email "vegetable9981@gmail.com"
```

*(请把 `your-github-email@example.com` 替换成您注册 GitHub 时使用的邮箱地址)*



### 第 1 步：在 GitHub 网站创建【空】仓库



1. 登录 GitHub，点击右上角的 **"+"** 号，选择 **"New repository"**。

2. 填写您的**仓库名称**（例如：`fpga-contest-project`）。

3. **（最重要的一步）** 确保仓库是**完全空白**的。

   - **不要**勾选 "Add a README file"。
   - **不要**勾选 "Add .gitignore"。
   - **不要**勾选 "Choose a license"。

4. 点击绿色的 **"Create repository"** 按钮。

5. 创建完成后，不要关闭页面。复制页面中间显示的 HTTPS 链接。它看起来像这样：

   https://github.com/YourUsername/fpga-contest-project.git

------



### 第 2 步：在【本地】项目文件夹中初始化 Git



1. 打开您的本地项目文件夹（即包含您所有 `src`、`tb` 文件夹和设计报告的**根目录**）。

2. 在此文件夹中**右键**，选择 **"Git Bash Here"** (Windows) 或打开您的终端 (Mac/Linux)。

3. 在打开的命令行窗口中，输入以下命令并按回车：

   Bash

   ```
   git init
   ```

4. （HLS 项目的关键步骤！）创建 .gitignore 文件。

   这一步是为了告诉 Git 忽略 HLS 自动生成的 solution1、proj_* 等临时文件，否则您可能会上传几个 G 的垃圾文件。

5. 在**同一个终端**里，输入 `touch .gitignore` 来创建文件，然后用记事本或代码编辑器打开这个刚创建的 `.gitignore` 文件，把下面这些 HLS 相关的忽略规则**全部复制进去**：

   ```
   # Vitis HLS project files
   solution*/
   proj_*/
   .project
   .settings
   
   # HLS report/log files
   *.log
   *.rpt
   *.jou
   
   # C simulation files
   csim/
   csim.exe
   
   # Other build artifacts
   *.o
   *.a
   ```

6. **保存并关闭** `.gitignore` 文件。

------



### 第 3 步：在【本地】提交您的所有代码



1. 回到您的 Git Bash / 终端。

2. 输入以下命令，将所有（未被忽略的）文件添加到 Git 的“暂存区”：

   Bash

   ```
   git add .
   ```

   *(注意 `add` 和 `.` 之间有空格)*

3. 输入以下命令，将文件正式“提交”到您本地的 Git 仓库：

   Bash

   ```
   git commit -m "补充"
   ```

   *(`-m` 后面是本次提交的说明，您可以自己修改)*

------



### 第 4 步：连接到 GitHub 并【上传】



1. 输入以下命令，确保您的主分支叫做 `main`（这是 GitHub 的新标准）：

   Bash

   ```
   git branch -M main
   ```

2. 输入以下命令，将您的本地仓库与您在第 1 步创建的 GitHub 远程仓库关联起来（**请粘贴您自己的 HTTPS 链接**）：

   Bash

   ```
   git remote add origin https://github.com/Shaojie-bit/hbut_miniapp.git
   ```

3. 最后，输入以下命令，将您本地的 `main` 分支推送到 GitHub：

   Bash

   ```
   git push -u origin main
   ```

4. **登录：** 此时，Git 可能会弹出一个窗口或在终端提示您**登录 GitHub**。登录成功后，它就会开始上传您的所有文件。

------

上传完成后，刷新您的 GitHub 仓库页面，就能看到所有文件了。这个流程（尤其是第 2 步的 `.gitignore`）能确保您的 HLS 仓库干净且专业。

------

### 第 5 步：创建新分支并打标签（进阶操作）

当您需要开发新功能或发布特定版本时，创建分支和打标签是非常重要的操作。

#### 1. 创建并切换到新分支

假设您要修复一个 bug 或开发一个新特性，最好不要直接在 `main` 分支上修改。

在终端中输入以下命令创建并切换到一个名为 `dev-v1.1` 的新分支：

Bash

```
git checkout -b dev-v1.1
```

*(这条命令相当于执行了 `git branch dev-v1.1` 和 `git checkout dev-v1.1` 两步)*

在此分支上，您可以继续修改代码、`git add .` 和 `git commit -m "..."`，这些更改最初只会保存在本地的 `dev-v1.1` 分支中。

#### 2. 推送新分支到 GitHub

当您在本地分支完成了一些提交后，可以将其推送到 GitHub：

Bash

```
git push -u origin dev-v1.1
```

刷新 GitHub 页面，点击分支下拉菜单（通常显示 `main`），您现在应该能看到 `dev-v1.1` 分支了。

#### 3. 打上版本标签 (Tag)

如果您认为当前的代码已经达到一个稳定的状态，可以给它打上一个版本号（例如 `v1.1`）。

**创建标签：**

Bash

```
git tag -a v1.1 -m "Release version 1.1"
```

*(`-a` 表示创建一个带注解的标签，`-m` 后面是标签说明)*

**推送标签到 GitHub：**

默认情况下，`git push` 不会把标签推送到远程服务器，您需要显式地推送标签：

Bash

```
git push origin v1.1
```

现在，在 GitHub 仓库页面的右侧 "Releases" 或 "Tags" 区域，您可以看到刚才发布的 `v1.1` 版本。

------

### 第 6 步：发布新版本而不覆盖 Main（推荐）

如果您想发布一个新的版本（比如 V3.0），但**不想覆盖** `main` 分支上现有的旧代码，请使用**新分支**的方式提交。

1. **创建并切换到新分支**
   
   首先，为您的新版本创建一个独立的分支（例如 `release-v3.0`）。
   
   Bash
   
   ```
   git checkout -b release-v3.0
   ```
   *(这样您的 `main` 分支会保持原状，所有的修改都会保存在这个新分支里)*

2. **保存并提交更改**
   
   将所有文件的修改提交到这个新分支。
   
   Bash
   
   ```
   git add .
   git commit -m "Release version 3.0"
   ```

3. **推送新分支到 GitHub**
   
   把这个新分支上传到服务器。
   
   Bash
   
   ```
   git push -u origin release-v3.0
   ```

4. **打上版本标签 (Tag)**
   
   给这个新分支打上正式的版本号标签。
   
   Bash
   
   ```
   git tag -a v3.0 -m "Tag for version 3.0"
   git push origin v3.0
   ```

这样，您的 GitHub 上既保留了旧的 `main` 页内容，又多了一个 `release-v3.0` 分支和 `v3.0` 标签，两者互不干扰。

