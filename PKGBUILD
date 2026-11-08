pkgname=stack-pdf-merger
pkgver=1.0.1
pkgrel=1
pkgdesc='A local desktop app for merging PDF files'
arch=('any')
license=('custom:MIT')
depends=('python' 'pyside6' 'poppler')
source=('app.py' 'stack.desktop' 'LICENSE')
sha256sums=('SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm755 "$srcdir/app.py" "$pkgdir/usr/share/stack-pdf-merger/app.py"
  install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/stack-pdf-merger/LICENSE"
  install -Dm644 "$srcdir/stack.desktop" "$pkgdir/usr/share/applications/stack-pdf-merger.desktop"
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/stack-pdf-merger" <<'EOF'
#!/bin/sh
exec python3 /usr/share/stack-pdf-merger/app.py "$@"
EOF
  chmod 755 "$pkgdir/usr/bin/stack-pdf-merger"
}
