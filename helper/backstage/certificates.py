"""Certificates for the phone page, made on this computer.

A small certificate authority (CA) signs a certificate for the laptop's
current network address. Install the CA on the phone once and the page opens
without a warning, even after the address changes. Until then the phone warns
once, and the fingerprint shown on the island's Phone tab tells you it is
really your laptop.

The CA is limited to private network addresses (name constraints), so even
if its key leaked it could not be used to fake any public website.

Files, all owner-only, in ~/.local/state/backstage/tls/:
    ca.pem, ca-key.pem          the CA, kept for CA_YEARS
    server.pem, server-key.pem  the page's certificate, remade when the
                                address changes or it is near its end
"""

import datetime
import ipaddress
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_YEARS = 10
# Phones refuse server certificates valid for much longer than a year.
SERVER_DAYS = 390
RENEW_DAYS = 30
CA_NAME = "Backstage on this laptop"
# The only addresses the CA may vouch for: home and office networks, loopback.
PRIVATE_NETWORKS = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _save(path, data):
    path.write_bytes(data)
    path.chmod(0o600)


def _key_bytes(key):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def fingerprint(cert):
    """SHA-256 fingerprint as browsers show it, e.g. "AB:12:...". """
    return cert.fingerprint(hashes.SHA256()).hex(":").upper()


class Certificates:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.ca_file = self.folder / "ca.pem"
        self._ca_key_file = self.folder / "ca-key.pem"
        self._server_file = self.folder / "server.pem"
        self._server_key_file = self.folder / "server-key.pem"
        self.ca_cert, self._ca_key = self._load_ca()

    @property
    def ca_bytes(self):
        """The CA in DER form, the format phones install from a download."""
        return self.ca_cert.public_bytes(serialization.Encoding.DER)

    def context(self, address):
        """TLS settings for serving the page at this IPv4 address. Also
        returns the server certificate's fingerprint."""
        cert = self._server_cert(address)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self._server_file, self._server_key_file)
        return context, fingerprint(cert)

    def _load_ca(self):
        if self.ca_file.exists() and self._ca_key_file.exists():
            cert = x509.load_pem_x509_certificate(self.ca_file.read_bytes())
            if cert.not_valid_after_utc > _now() + datetime.timedelta(days=SERVER_DAYS):
                key = serialization.load_pem_private_key(self._ca_key_file.read_bytes(), None)
                return cert, key
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_NAME)])
        constraints = x509.NameConstraints(
            permitted_subtrees=[x509.IPAddress(ipaddress.ip_network(n)) for n in PRIVATE_NETWORKS]
            + [x509.DNSName("backstage.invalid")],
            excluded_subtrees=None)
        cert = (x509.CertificateBuilder()
                .subject_name(name).issuer_name(name)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(_now() - datetime.timedelta(days=1))
                .not_valid_after(_now() + datetime.timedelta(days=365 * CA_YEARS))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False),
                               critical=True)
                .add_extension(constraints, critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                .sign(key, hashes.SHA256()))
        _save(self._ca_key_file, _key_bytes(key))
        _save(self.ca_file, cert.public_bytes(serialization.Encoding.PEM))
        # A new CA makes the old server certificate useless.
        self._server_file.unlink(missing_ok=True)
        return cert, key

    def _server_cert(self, address):
        ip = ipaddress.ip_address(address)
        if self._server_file.exists() and self._server_key_file.exists():
            cert = x509.load_pem_x509_certificate(self._server_file.read_bytes())
            names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            fresh = cert.not_valid_after_utc > _now() + datetime.timedelta(days=RENEW_DAYS)
            if fresh and cert.issuer == self.ca_cert.subject and ip in names.get_values_for_type(x509.IPAddress):
                return cert
        key = ec.generate_private_key(ec.SECP256R1())
        cert = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Backstage phone page")]))
                .issuer_name(self.ca_cert.subject)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(_now() - datetime.timedelta(days=1))
                .not_valid_after(_now() + datetime.timedelta(days=SERVER_DAYS))
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip)]), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self._ca_key.public_key()),
                               critical=False)
                .sign(self._ca_key, hashes.SHA256()))
        _save(self._server_key_file, _key_bytes(key))
        _save(self._server_file, cert.public_bytes(serialization.Encoding.PEM))
        return cert
