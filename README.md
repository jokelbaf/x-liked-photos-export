# x-liked-photos-export

A simple tool that allows you download all your liked photos from X (Twitter).

## Usage

> [!WARNING]  
> If you are logged in in multiple browsers with different accounts, you might get a 403 error because of cookies mismatch. In this case, you should provide the cookies manually, as shown [below](#cookies).

1. Download prebuilt binary from [here](https://github.com/jokelbaf/x-liked-photos-export/releases/latest).
2. Go to [x.com](https://x.com) and authorize.
3. Open devtools via `F12` and go to `Network` tab.
4. Copy the `X-Csrf-Token` header value from any request.
5. Go to the folder where you downloaded the binary, open terminal and run the following command:

```bash
./x-liked-photos-export-win-x64.exe --token <token>
```

This will fetch all posts you liked and generate a **data.json** file with links to the photos.

## Downloading photos

In case you want to download the photos, add `--download` flag:

```bash
./x-liked-photos-export-win-x64.exe --token <token> --download
```

## Cookies

By default the tool will extract the cookies from your browser to perform requests to the API on your behalf. If you want to provide the cookies manually, you can do so by using the `--cookies` flag:

```bash
./x-liked-photos-export-win-x64.exe --cookies <cookies> --token <token>
```

> [!NOTE]  
> Cookies must be in raw unparsed format, copied from the `Cookie` header. Similar to this:
> ```
> cookie1=value1; cookie2=value2; ...
> ```
